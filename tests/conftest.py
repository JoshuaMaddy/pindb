"""
Root conftest — sets up the test database, session isolation, Meilisearch mock,
FastAPI TestClient, and shared auth fixtures.

IMPORTANT: pytest-env (configured in pyproject.toml) sets the required env vars
(DATABASE_CONNECTION, MEILISEARCH_KEY, SECRET_KEY, IMAGE_DIRECTORY) during pytest
startup, BEFORE this file is imported. That satisfies Configuration()'s required
fields at import time. The real test DB connection is injected later via
session_maker.configure() in patch_session_maker.
"""

from __future__ import annotations

import importlib
import os
import secrets
import subprocess
from collections.abc import Generator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

# Ensure the image directory exists before pindb is imported (CONFIGURATION reads it)
os.makedirs(os.environ.get("IMAGE_DIRECTORY", "/tmp/pindb_test_images"), exist_ok=True)

# Import the app and internal modules we need to patch.
# meili_client.index() creates a Python object only — no network calls at import time.
#
# IMPORTANT: pindb/__init__.py does `from pindb.routes import search`, which sets the
# `pindb.search` ATTRIBUTE on the pindb module to `pindb.routes.search`. This shadows
# the actual pindb.search package at attribute-access level. Consequently, the `import
# pindb.search.X as alias` syntax fails because it traverses attributes (pindb → .search
# → .X) rather than using sys.modules directly.
#
# Fix: use importlib.import_module() which looks up sys.modules["pindb.search.X"]
# directly, bypassing the shadowed attribute.
from pindb import app  # noqa: E402  — this triggers all transitive imports

import pindb.database as _pindb_db  # noqa: E402  — safe; no attribute shadowing

# Must use importlib to avoid the pindb.search attribute-shadowing issue described above.
_search_update = importlib.import_module("pindb.search.update")
_search_search = importlib.import_module("pindb.search.search")

_REPO_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Session-scoped: PostgreSQL testcontainer + test engine
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def pg_container():
    """Spin up a real Postgres 17 container for the entire test session."""
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:17-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def test_engine(pg_container) -> Generator[Engine, None, None]:
    """
    Create a SQLAlchemy engine pointed at the testcontainers Postgres,
    then run alembic migrations (the real ones, not create_all).
    """
    url: str = pg_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+psycopg://"
    )
    engine = create_engine(url, echo=False)

    env = {**os.environ, "DATABASE_CONNECTION": url}
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        env=env,
        check=True,
        cwd=str(_REPO_ROOT),
    )

    yield engine
    engine.dispose()


# ---------------------------------------------------------------------------
# Function-scoped: connection with outer transaction (rolls back after each test)
# ---------------------------------------------------------------------------


@pytest.fixture
def db_connection(test_engine):
    """
    Open a single connection with a transaction that is NEVER committed.
    Everything written during the test is rolled back at teardown.
    """
    with test_engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()


# ---------------------------------------------------------------------------
# autouse: reconfigure session_maker in-place so all 28 route modules
# automatically use the test connection with savepoint isolation.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def patch_session_maker(db_connection):
    """
    Reconfigure the shared session_maker instance in-place.

    All route modules hold a reference to the SAME sessionmaker object, so
    configure() affects all of them without needing per-module monkeypatching.

    join_transaction_mode="create_savepoint": when a route calls
    session_maker.begin(), SQLAlchemy issues SAVEPOINT instead of BEGIN.
    On success the savepoint is released; on error it rolls back to it.
    The outer test transaction is never committed, so all writes vanish.
    """
    original_kw = dict(_pindb_db.session_maker.kw)

    _pindb_db.session_maker.configure(
        bind=db_connection,
        join_transaction_mode="create_savepoint",
    )

    yield

    _pindb_db.session_maker.kw.clear()
    _pindb_db.session_maker.kw.update(original_kw)


# ---------------------------------------------------------------------------
# autouse: mock Meilisearch PIN_INDEX on every test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def patch_meilisearch(monkeypatch) -> MagicMock:
    """
    Replace the module-level PIN_INDEX in both search modules with a MagicMock.
    Tests that need custom search results can configure mock_index.search.return_value.
    Add @pytest.mark.meili to use a real Meilisearch container instead.
    """
    mock_index = MagicMock()
    mock_index.search.return_value = {
        "hits": [],
        "offset": 0,
        "limit": 20,
        "estimatedTotalHits": 0,
        "processingTimeMs": 1,
        "query": "",
    }
    mock_index.add_documents.return_value = MagicMock(task_uid=1)
    mock_index.delete_document.return_value = MagicMock(task_uid=2)
    mock_index.delete_documents.return_value = MagicMock(task_uid=3)
    mock_index.get_documents.return_value = MagicMock(results=[], total=0)
    mock_index.update_searchable_attributes.return_value = MagicMock(task_uid=4)

    monkeypatch.setattr(_search_update, "PIN_INDEX", mock_index)
    monkeypatch.setattr(_search_search, "PIN_INDEX", mock_index)

    return mock_index


# ---------------------------------------------------------------------------
# Session-scoped: FastAPI app with lifespan disabled
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def test_app():
    """
    Replace the app's lifespan with a no-op to prevent:
      - APScheduler starting a background thread
      - Meilisearch index setup (setup_index / update_all)
      - Currency seeding and admin bootstrap (handled by explicit fixtures)
    """

    @asynccontextmanager
    async def null_lifespan(_app):
        yield

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = null_lifespan
    yield app
    app.router.lifespan_context = original_lifespan


# ---------------------------------------------------------------------------
# Function-scoped: TestClient and db_session
# ---------------------------------------------------------------------------


@pytest.fixture
def client(test_app, patch_session_maker, patch_meilisearch):
    """Unauthenticated Starlette TestClient."""
    from starlette.testclient import TestClient

    with TestClient(test_app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def db_session(patch_session_maker) -> Generator[Session, None, None]:
    """
    A SQLAlchemy Session for direct DB manipulation in tests.
    Uses the patched session_maker (bound to the test connection).
    """
    session = _pindb_db.session_maker()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Seeding and user fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def seed_currencies(db_session: Session) -> None:
    """Seed currencies into the test DB (mirrors lifespan behaviour)."""
    from pindb.database import seed_currencies as _seed

    _seed()
    db_session.flush()


@pytest.fixture
def test_user(db_session: Session, seed_currencies):
    """Regular (non-admin) user, flushed but not committed."""
    from pindb.auth import hash_password
    from pindb.database.user import User

    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("testpassword"),
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def admin_user(db_session: Session, seed_currencies):
    """Admin user, flushed but not committed."""
    from pindb.auth import hash_password
    from pindb.database.user import User

    user = User(
        username="adminuser",
        email="admin@example.com",
        hashed_password=hash_password("adminpassword"),
        is_admin=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _make_session_token(user, db_session: Session) -> str:
    """Insert a UserSession row and return its token."""
    from pindb.database.session import UserSession

    token = secrets.token_urlsafe(32)
    db_session.add(
        UserSession(
            token=token,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None)
            + timedelta(days=30),
        )
    )
    db_session.flush()
    return token


@pytest.fixture
def auth_client(client, test_user, db_session: Session):
    """TestClient pre-authenticated as test_user."""
    token = _make_session_token(test_user, db_session)
    client.cookies.set("session", token)
    return client


@pytest.fixture
def admin_client(client, admin_user, db_session: Session):
    """TestClient pre-authenticated as admin_user."""
    token = _make_session_token(admin_user, db_session)
    client.cookies.set("session", token)
    return client


# ---------------------------------------------------------------------------
# Factory session wiring (autouse — wires factories to db_session per test)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def bind_factories(db_session: Session):
    """Wire all factory_boy factories to the current test's session."""
    try:
        import tests.factories.base as _base

        _base._current_session = db_session
        yield
        _base._current_session = None
    except ImportError:
        yield
