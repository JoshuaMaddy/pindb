"""Integration tests for /user/pins/* collection routes (owned and wanted)."""

from typing import cast

import pytest

from pindb.database.pin import Pin
from tests.factories.pin import PinFactory
from tests.fixtures.users import SUBJECT_USER_PARAMS


@pytest.mark.integration
class TestAddOwnedPin:
    def test_unauthenticated_returns_401(self, client, db_session):
        pin = cast(Pin, PinFactory())
        response = client.post(f"/user/pins/{pin.id}/owned")
        assert response.status_code == 401

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_authenticated_adds_owned_pin(
        self, auth_client_as_subject, db_session, subject_user
    ):
        from sqlalchemy import select

        from pindb.database import UserOwnedPin

        pin = cast(Pin, PinFactory())
        response = auth_client_as_subject.post(
            f"/user/pins/{pin.id}/owned",
            data={"quantity": "1"},
        )
        # Non-HTMX request returns 204
        assert response.status_code == 204

        entry = db_session.scalars(
            select(UserOwnedPin).where(
                UserOwnedPin.user_id == subject_user.id,
                UserOwnedPin.pin_id == pin.id,
            )
        ).first()
        assert entry is not None
        assert entry.quantity == 1

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_nonexistent_pin_returns_404(self, auth_client_as_subject):
        response = auth_client_as_subject.post(
            "/user/pins/999999/owned",
            data={"quantity": "1"},
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestRemoveOwnedPin:
    def test_unauthenticated_returns_401(self, client, db_session):
        pin = cast(Pin, PinFactory())
        response = client.delete(f"/user/pins/{pin.id}/owned/1")
        assert response.status_code == 401

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_remove_owned_pin(self, auth_client_as_subject, db_session, subject_user):
        from sqlalchemy import select

        from pindb.database import UserOwnedPin

        pin = cast(Pin, PinFactory())
        # Create an owned entry directly
        entry = UserOwnedPin(
            user_id=subject_user.id,
            pin_id=pin.id,
            grade_id=None,
        )
        db_session.add(entry)
        db_session.flush()
        entry_id = entry.id

        response = auth_client_as_subject.delete(
            f"/user/pins/{pin.id}/owned/{entry_id}"
        )
        assert response.status_code == 204

        remaining = db_session.scalars(
            select(UserOwnedPin).where(UserOwnedPin.id == entry_id)
        ).first()
        assert remaining is None

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_cannot_remove_other_users_entry(
        self, auth_client_as_subject, db_session, admin_user
    ):
        from pindb.database import UserOwnedPin

        pin = cast(Pin, PinFactory())
        entry = UserOwnedPin(
            user_id=admin_user.id,
            pin_id=pin.id,
            grade_id=None,
        )
        db_session.add(entry)
        db_session.flush()

        response = auth_client_as_subject.delete(
            f"/user/pins/{pin.id}/owned/{entry.id}"
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestAddWantedPin:
    def test_unauthenticated_returns_401(self, client, db_session):
        pin = cast(Pin, PinFactory())
        response = client.post(f"/user/pins/{pin.id}/wanted")
        assert response.status_code == 401

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_authenticated_adds_wanted_pin(
        self, auth_client_as_subject, db_session, subject_user
    ):
        from sqlalchemy import select

        from pindb.database import UserWantedPin

        pin = cast(Pin, PinFactory())
        response = auth_client_as_subject.post(
            f"/user/pins/{pin.id}/wanted",
            data={},
        )
        assert response.status_code == 204

        entry = db_session.scalars(
            select(UserWantedPin).where(
                UserWantedPin.user_id == subject_user.id,
                UserWantedPin.pin_id == pin.id,
            )
        ).first()
        assert entry is not None

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_duplicate_wanted_is_idempotent(
        self, auth_client_as_subject, db_session, subject_user
    ):
        from sqlalchemy import select

        from pindb.database import UserWantedPin

        pin = cast(Pin, PinFactory())
        auth_client_as_subject.post(f"/user/pins/{pin.id}/wanted", data={})
        auth_client_as_subject.post(f"/user/pins/{pin.id}/wanted", data={})

        entries = db_session.scalars(
            select(UserWantedPin).where(
                UserWantedPin.user_id == subject_user.id,
                UserWantedPin.pin_id == pin.id,
            )
        ).all()
        assert len(entries) == 1


@pytest.mark.integration
class TestRemoveWantedPin:
    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_remove_wanted_pin(self, auth_client_as_subject, db_session, subject_user):
        from sqlalchemy import select

        from pindb.database import UserWantedPin

        pin = cast(Pin, PinFactory())
        entry = UserWantedPin(
            user_id=subject_user.id,
            pin_id=pin.id,
            grade_id=None,
        )
        db_session.add(entry)
        db_session.flush()
        entry_id = entry.id

        response = auth_client_as_subject.delete(
            f"/user/pins/{pin.id}/wanted/{entry_id}"
        )
        assert response.status_code == 204

        remaining = db_session.scalars(
            select(UserWantedPin).where(UserWantedPin.id == entry_id)
        ).first()
        assert remaining is None
