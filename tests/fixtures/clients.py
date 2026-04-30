"""Starlette TestClient and raw ORM session."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session

from tests.fixtures import core


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
    session = core.pindb_database.session_maker()
    yield session
    session.close()
