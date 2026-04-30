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
from csv import DictReader
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool
from sqlalchemy.sql.dml import Delete, Insert, Update

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
import pindb.database as _pindb_db  # noqa: E402  — safe; no attribute shadowing
from pindb import app  # noqa: E402  — this triggers all transitive imports

# Must use importlib to avoid the pindb.search attribute-shadowing issue described above.
_search_update = importlib.import_module("pindb.search.update")
_search_search = importlib.import_module("pindb.search.search")

_REPO_ROOT = Path(__file__).parent.parent
_CURRENCY_ROWS: list[dict[str, int | str]] | None = None


def _is_unit_or_e2e_test(request: pytest.FixtureRequest) -> bool:
    return "tests" in request.node.path.parts and (
        "unit" in request.node.path.parts or "e2e" in request.node.path.parts
    )


def _currency_rows() -> list[dict[str, int | str]]:
    global _CURRENCY_ROWS
    if _CURRENCY_ROWS is None:
        currencies_path = (
            _REPO_ROOT / "src" / "pindb" / "database" / "data" / "currencies.csv"
        )
        with currencies_path.open(newline="") as currencies_file:
            _CURRENCY_ROWS = [
                {
                    "id": int(row["id"]),
                    "name": row["name"],
                    "code": row["code"],
                }
                for row in DictReader(currencies_file)
            ]
    return _CURRENCY_ROWS


class AutoCommitSession(Session):
    """Test session that makes fixture ``flush()`` calls visible to async routes."""

    _committing: bool = False
    _needs_commit: bool = False

    def commit(self) -> None:
        self._committing = True
        try:
            super().commit()
            self._needs_commit = False
        finally:
            self._committing = False

    def flush(self, objects=None) -> None:  # type: ignore[no-untyped-def]
        had_changes = bool(self.new or self.dirty or self.deleted)
        super().flush(objects=objects)
        if (
            (had_changes or self._needs_commit)
            and self.in_transaction()
            and not self._committing
        ):
            self.commit()

    def execute(self, statement, *args, **kwargs):  # type: ignore[no-untyped-def]
        result = super().execute(statement, *args, **kwargs)
        if isinstance(statement, (Delete, Insert, Update)):
            self._needs_commit = True
        return result


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
    async_url: str = url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
    engine = create_engine(url, echo=False)

    env = {
        **os.environ,
        "DATABASE_CONNECTION": async_url,
        "DATABASE_CONNECTION_SYNC": url,
    }
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        env=env,
        check=True,
        cwd=str(_REPO_ROOT),
    )

    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def test_async_engine(test_engine: Engine) -> Generator[AsyncEngine, None, None]:
    """Async engine pointed at the same testcontainer database as ``test_engine``."""
    import asyncio

    sync_url = test_engine.url.render_as_string(hide_password=False)
    async_url = sync_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
    async_engine = create_async_engine(async_url, poolclass=NullPool)

    yield async_engine
    asyncio.run(async_engine.dispose())


# ---------------------------------------------------------------------------
# Function-scoped: connection with outer transaction (rolls back after each test)
# ---------------------------------------------------------------------------


@pytest.fixture
def db_connection(test_engine: Engine) -> Generator[Connection, None, None]:
    """
    Open a single sync connection for direct DB setup/assertions in tests.
    """
    with test_engine.connect() as connection:
        yield connection


@pytest.fixture(scope="session")
def truncate_sql() -> str:
    """Precomputed cleanup SQL for integration tests."""
    from pindb.database.base import Base

    table_names = [
        table.name
        for table in reversed(Base.metadata.sorted_tables)
        if table.name != "alembic_version"
    ]
    return f"TRUNCATE TABLE {', '.join(table_names)} RESTART IDENTITY CASCADE"


# ---------------------------------------------------------------------------
# autouse: reconfigure session_maker in-place so all 28 route modules
# automatically use the test connection with savepoint isolation.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def patch_session_maker(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """
    Reconfigure the shared session_maker instance in-place.

    All route modules hold a reference to the SAME sessionmaker object, so
    configure() affects all of them without needing per-module monkeypatching.

    join_transaction_mode="create_savepoint": when a route calls
    session_maker.begin(), SQLAlchemy issues SAVEPOINT instead of BEGIN.
    On success the savepoint is released; on error it rolls back to it.
    The outer test transaction is never committed, so all writes vanish.
    """
    if _is_unit_or_e2e_test(request=request):
        yield
        return

    db_connection: Connection = request.getfixturevalue("db_connection")
    test_async_engine: AsyncEngine = request.getfixturevalue("test_async_engine")
    cleanup_sql: str = request.getfixturevalue("truncate_sql")

    original_kw = dict(_pindb_db.session_maker.kw)
    original_class = _pindb_db.session_maker.class_
    original_async_kw = dict(_pindb_db.async_session_maker.kw)

    _pindb_db.session_maker.configure(
        bind=db_connection,
    )
    _pindb_db.session_maker.class_ = AutoCommitSession
    _pindb_db.async_session_maker.configure(bind=test_async_engine)

    yield

    _pindb_db.session_maker.kw.clear()
    _pindb_db.session_maker.kw.update(original_kw)
    _pindb_db.session_maker.class_ = original_class
    _pindb_db.async_session_maker.kw.clear()
    _pindb_db.async_session_maker.kw.update(original_async_kw)

    db_connection.execute(text(cleanup_sql))
    db_connection.commit()


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
    mock_index.search = AsyncMock(
        return_value={
            "hits": [],
            "offset": 0,
            "limit": 20,
            "estimatedTotalHits": 0,
            "processingTimeMs": 1,
            "query": "",
        }
    )
    mock_index.add_documents = AsyncMock(return_value=MagicMock(task_uid=1))
    mock_index.delete_document = AsyncMock(return_value=MagicMock(task_uid=2))
    mock_index.delete_documents = AsyncMock(return_value=MagicMock(task_uid=3))
    mock_index.get_documents = AsyncMock(return_value=MagicMock(results=[], total=0))
    mock_index.update_searchable_attributes = AsyncMock(
        return_value=MagicMock(task_uid=4)
    )
    mock_index.update_filterable_attributes = AsyncMock(
        return_value=MagicMock(task_uid=5)
    )
    if hasattr(_search_update, "PIN_INDEX"):
        monkeypatch.setattr(_search_update, "PIN_INDEX", mock_index)
    for name in (
        "_pin_index",
        "_tags_index",
        "_artists_index",
        "_shops_index",
        "_pin_sets_index",
    ):
        if hasattr(_search_update, name):
            monkeypatch.setattr(_search_update, name, lambda: mock_index)
    monkeypatch.setattr(_search_search, "PIN_INDEX", mock_index)
    # Also stub the secondary indexes used by update_all / bulk options.
    for name in ("TAGS_INDEX", "ARTISTS_INDEX", "SHOPS_INDEX", "PIN_SETS_INDEX"):
        if hasattr(_search_update, name):
            monkeypatch.setattr(_search_update, name, mock_index)

    # Patch INDEX_BY_ENTITY_TYPE so the generic update_one/update_many/delete_one
    # functions also use the mock instead of real (import-time) index objects.
    if hasattr(_search_update, "INDEX_BY_ENTITY_TYPE"):
        from pindb.database.entity_type import EntityType

        monkeypatch.setattr(
            _search_update,
            "INDEX_BY_ENTITY_TYPE",
            {et: mock_index for et in EntityType},
        )

    # Modules that import these names at top level need to be patched too.
    try:
        _bulk_pin = importlib.import_module("pindb.routes.bulk.pin")
        if hasattr(_bulk_pin, "TAGS_INDEX"):
            monkeypatch.setattr(_bulk_pin, "TAGS_INDEX", mock_index)
    except ImportError:
        pass

    for module_name in ("pindb.routes.get.options", "pindb.routes.get.tag"):
        try:
            module = importlib.import_module(module_name)
            for name in (
                "PIN_INDEX",
                "TAGS_INDEX",
                "ARTISTS_INDEX",
                "SHOPS_INDEX",
                "PIN_SETS_INDEX",
            ):
                if hasattr(module, name):
                    monkeypatch.setattr(module, name, mock_index)
        except ImportError:
            pass

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
def anon_client(test_app, patch_session_maker, patch_meilisearch):
    """A second unauthenticated TestClient, used when tests also need
    `admin_client`/`auth_client` (which both mutate the shared `client`'s cookies)."""
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
    from pindb.database.currency import Currency

    db_session.execute(
        pg_insert(Currency)
        .values(_currency_rows())
        .on_conflict_do_nothing(index_elements=[Currency.id])
    )
    db_session.commit()


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


@pytest.fixture
def editor_user(db_session: Session, seed_currencies):
    """Non-admin editor user. Creates pending entities; can edit own pending entries."""
    from pindb.auth import hash_password
    from pindb.database.user import User

    user = User(
        username="editoruser",
        email="editor@example.com",
        hashed_password=hash_password("editorpassword"),
        is_editor=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def other_editor_user(db_session: Session, seed_currencies):
    """A second editor, for ownership boundary tests."""
    from pindb.auth import hash_password
    from pindb.database.user import User

    user = User(
        username="editor2",
        email="editor2@example.com",
        hashed_password=hash_password("editor2password"),
        is_editor=True,
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
def auth_client(
    test_app, patch_session_maker, patch_meilisearch, test_user, db_session: Session
):
    """TestClient pre-authenticated as test_user.

    Uses its own TestClient instance so tests that mix multiple authenticated
    clients in one request do not have their session cookies clobbered.
    """
    from starlette.testclient import TestClient

    c = TestClient(test_app, raise_server_exceptions=True)
    token = _make_session_token(test_user, db_session)
    c.cookies.set("session", token)
    return c


@pytest.fixture
def admin_client(
    test_app, patch_session_maker, patch_meilisearch, admin_user, db_session: Session
):
    """TestClient pre-authenticated as admin_user.

    Uses its own TestClient instance so tests that mix multiple authenticated
    clients in one request do not have their session cookies clobbered.
    """
    from starlette.testclient import TestClient

    c = TestClient(test_app, raise_server_exceptions=True)
    token = _make_session_token(admin_user, db_session)
    c.cookies.set("session", token)
    return c


@pytest.fixture
def editor_client(
    test_app, patch_session_maker, patch_meilisearch, editor_user, db_session: Session
):
    """TestClient pre-authenticated as editor_user.

    Uses its own TestClient so tests that also use `admin_client`/`auth_client`
    don't have their session cookies clobbered on the shared `client`.
    """
    from starlette.testclient import TestClient

    c = TestClient(test_app, raise_server_exceptions=True)
    token = _make_session_token(editor_user, db_session)
    c.cookies.set("session", token)
    return c


@pytest.fixture
def other_editor_client(
    test_app,
    patch_session_maker,
    patch_meilisearch,
    other_editor_user,
    db_session: Session,
):
    """Pre-authenticated as a second editor."""
    from starlette.testclient import TestClient

    c = TestClient(test_app, raise_server_exceptions=True)
    token = _make_session_token(other_editor_user, db_session)
    c.cookies.set("session", token)
    return c


# ---------------------------------------------------------------------------
# Image fixtures — 1×1 PNG for Pin front_image uploads
# ---------------------------------------------------------------------------


@pytest.fixture
def png_bytes() -> bytes:
    """A valid 1×1 PNG byte string, PIL can open it."""
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color=(255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def png_upload(png_bytes: bytes):
    """Tuple suitable for TestClient files={"front_image": png_upload}."""
    return ("test.png", png_bytes, "image/png")


# ---------------------------------------------------------------------------
# Audit context reset — prevent ContextVar leakage between tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Clear in-memory rate-limit counters between tests so tests that
    share an endpoint (login, signup, password-change) do not inherit
    hits from earlier ones and trip 429 prematurely."""
    from pindb.rate_limit import reset_rate_limits

    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.fixture(autouse=True)
def _reset_audit_context():
    """Clear the audit user ContextVars before and after each test.

    The `attach_user_middleware` sets these on every request, but direct
    db_session writes (factories, fixtures) can leave them stale.
    """
    from pindb.audit_events import set_audit_user, set_audit_user_flags

    set_audit_user(None)
    set_audit_user_flags(is_admin=False, is_editor=False)
    yield
    set_audit_user(None)
    set_audit_user_flags(is_admin=False, is_editor=False)


# ---------------------------------------------------------------------------
# Factory session wiring (autouse — wires factories to db_session per test)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def bind_factories(request: pytest.FixtureRequest):
    """Wire all factory_boy factories to the current test's session."""
    if _is_unit_or_e2e_test(request=request):
        yield
        return

    db_session: Session = request.getfixturevalue("db_session")
    try:
        import tests.factories.base as _base

        _base._current_session = db_session
        yield
        _base._current_session = None
    except ImportError:
        yield
