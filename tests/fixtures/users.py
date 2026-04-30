"""Seed data, users, and authenticated TestClients."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from tests.fixtures import core


@pytest.fixture
def seed_currencies(db_session: Session) -> None:
    """Seed currencies into the test DB (mirrors lifespan behaviour)."""
    from pindb.database.currency import Currency

    db_session.execute(
        pg_insert(Currency)
        .values(core.currency_rows())
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
