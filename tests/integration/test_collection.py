"""Integration tests for /user/pins/* collection routes (owned and wanted)."""

import pytest

from tests.factories.pin import PinFactory


@pytest.mark.integration
class TestAddOwnedPin:
    def test_unauthenticated_returns_401(self, client, db_session):
        pin = PinFactory()
        response = client.post(f"/user/pins/{pin.id}/owned")  # ty:ignore[unresolved-attribute]
        assert response.status_code == 401

    def test_authenticated_adds_owned_pin(self, auth_client, db_session, test_user):
        from sqlalchemy import select

        from pindb.database import UserOwnedPin

        pin = PinFactory()
        response = auth_client.post(
            f"/user/pins/{pin.id}/owned",  # ty:ignore[unresolved-attribute]
            data={"quantity": "1"},
        )
        # Non-HTMX request returns 204
        assert response.status_code == 204

        entry = db_session.scalars(
            select(UserOwnedPin).where(
                UserOwnedPin.user_id == test_user.id,
                UserOwnedPin.pin_id == pin.id,  # ty:ignore[unresolved-attribute]
            )
        ).first()
        assert entry is not None
        assert entry.quantity == 1

    def test_nonexistent_pin_returns_404(self, auth_client):
        response = auth_client.post(
            "/user/pins/999999/owned",
            data={"quantity": "1"},
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestRemoveOwnedPin:
    def test_unauthenticated_returns_401(self, client, db_session):
        pin = PinFactory()
        response = client.delete(f"/user/pins/{pin.id}/owned/1")  # ty:ignore[unresolved-attribute]
        assert response.status_code == 401

    def test_remove_owned_pin(self, auth_client, db_session, test_user):
        from sqlalchemy import select

        from pindb.database import UserOwnedPin

        pin = PinFactory()
        # Create an owned entry directly
        entry = UserOwnedPin(user_id=test_user.id, pin_id=pin.id, grade_id=None)  # ty:ignore[unresolved-attribute]
        db_session.add(entry)
        db_session.flush()
        entry_id = entry.id

        response = auth_client.delete(f"/user/pins/{pin.id}/owned/{entry_id}")  # ty:ignore[unresolved-attribute]
        assert response.status_code == 204

        remaining = db_session.scalars(
            select(UserOwnedPin).where(UserOwnedPin.id == entry_id)
        ).first()
        assert remaining is None

    def test_cannot_remove_other_users_entry(self, auth_client, db_session, admin_user):
        from pindb.database import UserOwnedPin

        pin = PinFactory()
        entry = UserOwnedPin(user_id=admin_user.id, pin_id=pin.id, grade_id=None)  # ty:ignore[unresolved-attribute]
        db_session.add(entry)
        db_session.flush()

        response = auth_client.delete(f"/user/pins/{pin.id}/owned/{entry.id}")  # ty:ignore[unresolved-attribute]
        assert response.status_code == 404


@pytest.mark.integration
class TestAddWantedPin:
    def test_unauthenticated_returns_401(self, client, db_session):
        pin = PinFactory()
        response = client.post(f"/user/pins/{pin.id}/wanted")  # ty:ignore[unresolved-attribute]
        assert response.status_code == 401

    def test_authenticated_adds_wanted_pin(self, auth_client, db_session, test_user):
        from sqlalchemy import select

        from pindb.database import UserWantedPin

        pin = PinFactory()
        response = auth_client.post(
            f"/user/pins/{pin.id}/wanted",  # ty:ignore[unresolved-attribute]
            data={},
        )
        assert response.status_code == 204

        entry = db_session.scalars(
            select(UserWantedPin).where(
                UserWantedPin.user_id == test_user.id,
                UserWantedPin.pin_id == pin.id,  # ty:ignore[unresolved-attribute]
            )
        ).first()
        assert entry is not None

    def test_duplicate_wanted_is_idempotent(self, auth_client, db_session, test_user):
        from sqlalchemy import select

        from pindb.database import UserWantedPin

        pin = PinFactory()
        auth_client.post(f"/user/pins/{pin.id}/wanted", data={})  # ty:ignore[unresolved-attribute]
        auth_client.post(f"/user/pins/{pin.id}/wanted", data={})  # ty:ignore[unresolved-attribute]

        entries = db_session.scalars(
            select(UserWantedPin).where(
                UserWantedPin.user_id == test_user.id,
                UserWantedPin.pin_id == pin.id,  # ty:ignore[unresolved-attribute]
            )
        ).all()
        assert len(entries) == 1


@pytest.mark.integration
class TestRemoveWantedPin:
    def test_remove_wanted_pin(self, auth_client, db_session, test_user):
        from sqlalchemy import select

        from pindb.database import UserWantedPin

        pin = PinFactory()
        entry = UserWantedPin(user_id=test_user.id, pin_id=pin.id, grade_id=None)  # ty:ignore[unresolved-attribute]
        db_session.add(entry)
        db_session.flush()
        entry_id = entry.id

        response = auth_client.delete(f"/user/pins/{pin.id}/wanted/{entry_id}")  # ty:ignore[unresolved-attribute]
        assert response.status_code == 204

        remaining = db_session.scalars(
            select(UserWantedPin).where(UserWantedPin.id == entry_id)
        ).first()
        assert remaining is None
