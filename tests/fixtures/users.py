"""Seed data, users, and authenticated TestClients."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import cast

import pytest
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from tests.fixtures import core

MINIMAL_USER_USERNAME = "testuser"
FULL_PROFILE_USER_USERNAME = "fullprofileuser"


def _seed_full_profile_user_associations(
    db_session: Session, *, user: object, admin_user: object
) -> None:
    """Populate favorites, collection, wants, trades preview, and personal-set pins."""
    from pindb.database.joins import (
        pin_set_memberships,
        user_favorite_pin_sets,
        user_favorite_pins,
    )
    from pindb.database.pin import Pin
    from pindb.database.pin_set import PinSet
    from pindb.database.user import User as DbUser
    from pindb.database.user_owned_pin import UserOwnedPin
    from pindb.database.user_wanted_pin import UserWantedPin
    from tests.factories.artist import ArtistFactory
    from tests.factories.pin import PinFactory
    from tests.factories.pin_set import PersonalPinSetFactory, PinSetFactory
    from tests.factories.shop import ShopFactory

    user_row = cast(DbUser, user)
    admin_row = cast(DbUser, admin_user)

    shop = ShopFactory(name="FullProf Shop", approved=True, created_by=admin_row)
    artist = ArtistFactory(name="FullProf Artist", approved=True, created_by=admin_row)
    pin_alpha = cast(
        Pin,
        PinFactory(
            name="FullProf Alpha",
            shops={shop},
            artists={artist},
            approved=True,
            created_by=admin_row,
        ),
    )
    pin_beta = cast(
        Pin,
        PinFactory(
            name="FullProf Beta",
            shops={shop},
            artists={artist},
            approved=True,
            created_by=admin_row,
        ),
    )
    global_set = cast(
        PinSet,
        PinSetFactory(
            name="FullProf Curated Set",
            approved=True,
            created_by=admin_row,
        ),
    )
    personal = cast(
        PinSet,
        PersonalPinSetFactory(
            name="FullProf Personal Set",
            owner_id=user_row.id,
            approved=True,
            created_by=user_row,
        ),
    )
    db_session.execute(
        pin_set_memberships.insert().values(
            pin_id=pin_alpha.id,
            set_id=personal.id,
            position=0,
        )
    )
    db_session.execute(
        pin_set_memberships.insert().values(
            pin_id=pin_beta.id,
            set_id=personal.id,
            position=1,
        )
    )
    db_session.execute(
        user_favorite_pins.insert().values(
            user_id=user_row.id,
            pin_id=pin_alpha.id,
        )
    )
    db_session.execute(
        user_favorite_pins.insert().values(
            user_id=user_row.id,
            pin_id=pin_beta.id,
        )
    )
    db_session.execute(
        user_favorite_pin_sets.insert().values(
            user_id=user_row.id,
            pin_set_id=global_set.id,
        )
    )
    db_session.add(
        UserOwnedPin(
            user_id=user_row.id,
            pin_id=pin_alpha.id,
            grade_id=None,
            quantity=2,
            tradeable_quantity=1,
        )
    )
    db_session.add(
        UserOwnedPin(
            user_id=user_row.id,
            pin_id=pin_beta.id,
            grade_id=None,
            quantity=1,
            tradeable_quantity=0,
        )
    )
    db_session.add(
        UserWantedPin(user_id=user_row.id, pin_id=pin_beta.id, grade_id=None)
    )
    db_session.flush()


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
        username=MINIMAL_USER_USERNAME,
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


@pytest.fixture
def test_user_full_profile(db_session: Session, seed_currencies, admin_user):
    """Second regular user with favorites, lists, personal sets, and tradeables seeded."""
    from pindb.auth import hash_password
    from pindb.database.user import User

    user = User(
        username=FULL_PROFILE_USER_USERNAME,
        email="fullprofile@example.com",
        hashed_password=hash_password("testpassword"),
    )
    db_session.add(user)
    db_session.flush()
    _seed_full_profile_user_associations(db_session, user=user, admin_user=admin_user)
    return user


SUBJECT_USER_PARAMS = (
    pytest.param("minimal", id="minimal_user"),
    pytest.param("full_profile", id="full_profile_user"),
)


@pytest.fixture
def subject_user(request: pytest.FixtureRequest, test_user, test_user_full_profile):
    """Indirect-only: ``@pytest.mark.parametrize('subject_user', SUBJECT_USER_PARAMS, indirect=True)``."""
    param = getattr(request, "param", None)
    if param is None:
        pytest.fail(
            "subject_user requires @pytest.mark.parametrize(..., indirect=True)"
        )
    if param == "minimal":
        return test_user
    if param == "full_profile":
        return test_user_full_profile
    pytest.fail(f"unknown subject_user param: {param!r}")


@pytest.fixture
def auth_client_as_subject(
    subject_user,
    test_app,
    patch_session_maker,
    patch_meilisearch,
    db_session: Session,
):
    """Authenticated client whose session matches ``subject_user``."""
    from starlette.testclient import TestClient

    client = TestClient(test_app, raise_server_exceptions=True)
    token = _make_session_token(subject_user, db_session)
    client.cookies.set("session", token)
    return client
