"""`/user/favorites/pins/{id}` and `/user/favorites/sets/{id}` — POST to add,
DELETE to remove. Both endpoints must be idempotent."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from pindb.database.joins import user_favorite_pin_sets, user_favorite_pins
from tests.factories.pin import PinFactory
from tests.factories.pin_set import PersonalPinSetFactory


def _pin_fav_count(db_session, user_id, pin_id):
    return db_session.scalar(
        select(func.count())
        .select_from(user_favorite_pins)
        .where(
            user_favorite_pins.c.user_id == user_id,
            user_favorite_pins.c.pin_id == pin_id,
        )
    )


def _set_fav_count(db_session, user_id, set_id):
    return db_session.scalar(
        select(func.count())
        .select_from(user_favorite_pin_sets)
        .where(
            user_favorite_pin_sets.c.user_id == user_id,
            user_favorite_pin_sets.c.pin_set_id == set_id,
        )
    )


@pytest.mark.integration
class TestFavoritePin:
    def test_favorite_then_unfavorite(
        self, auth_client, db_session, test_user, admin_user
    ):
        pin = PinFactory(approved=True, created_by=admin_user)
        pin_id = pin.id  # ty:ignore[unresolved-attribute]

        fav = auth_client.post(f"/user/favorites/pins/{pin_id}")
        assert fav.status_code in (200, 204)
        db_session.expire_all()
        assert _pin_fav_count(db_session, test_user.id, pin_id) == 1

        unfav = auth_client.delete(f"/user/favorites/pins/{pin_id}")
        assert unfav.status_code in (200, 204)
        db_session.expire_all()
        assert _pin_fav_count(db_session, test_user.id, pin_id) == 0

    def test_favorite_is_idempotent(
        self, auth_client, db_session, test_user, admin_user
    ):
        pin = PinFactory(approved=True, created_by=admin_user)
        pin_id = pin.id  # ty:ignore[unresolved-attribute]

        auth_client.post(f"/user/favorites/pins/{pin_id}")
        auth_client.post(f"/user/favorites/pins/{pin_id}")
        db_session.expire_all()
        assert _pin_fav_count(db_session, test_user.id, pin_id) == 1

    def test_unfavorite_missing_is_idempotent(
        self, auth_client, db_session, test_user, admin_user
    ):
        pin = PinFactory(approved=True, created_by=admin_user)
        response = auth_client.delete(f"/user/favorites/pins/{pin.id}")  # ty:ignore[unresolved-attribute]
        assert response.status_code in (200, 204)

    def test_guest_rejected(self, anon_client):
        response = anon_client.post("/user/favorites/pins/1")
        assert response.status_code in (401, 403)


@pytest.mark.integration
class TestFavoritePinSet:
    def test_favorite_then_unfavorite_set(
        self, auth_client, db_session, test_user, admin_user
    ):
        pin_set = PersonalPinSetFactory(owner_id=admin_user.id, name="Curated")
        set_id = pin_set.id  # ty:ignore[unresolved-attribute]

        fav = auth_client.post(f"/user/favorites/sets/{set_id}")
        assert fav.status_code in (200, 204, 303)
        db_session.expire_all()
        assert _set_fav_count(db_session, test_user.id, set_id) == 1

        unfav = auth_client.delete(f"/user/favorites/sets/{set_id}")
        assert unfav.status_code in (200, 204, 303)
        db_session.expire_all()
        assert _set_fav_count(db_session, test_user.id, set_id) == 0

    def test_favorite_set_is_idempotent(
        self, auth_client, db_session, test_user, admin_user
    ):
        pin_set = PersonalPinSetFactory(owner_id=admin_user.id, name="Curated")
        set_id = pin_set.id  # ty:ignore[unresolved-attribute]

        auth_client.post(f"/user/favorites/sets/{set_id}")
        auth_client.post(f"/user/favorites/sets/{set_id}")
        db_session.expire_all()
        assert _set_fav_count(db_session, test_user.id, set_id) == 1
