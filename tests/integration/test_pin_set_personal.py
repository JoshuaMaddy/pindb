"""Personal-set CRUD + ownership guard + promote-to-global + pin reorder."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from pindb.database import PinSet
from pindb.database.joins import pin_set_memberships
from tests.factories.pin import PinFactory
from tests.factories.pin_set import PersonalPinSetFactory
from tests.fixtures.users import SUBJECT_USER_PARAMS


@pytest.mark.integration
class TestPersonalSetCrud:
    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_authenticated_user_can_create_personal_set(
        self, auth_client_as_subject, db_session, subject_user
    ):
        response = auth_client_as_subject.post(
            "/user/me/sets",
            data={"name": "My Fav Pins", "description": "stuff I like"},
            follow_redirects=False,
        )
        assert response.status_code == 303

        db_session.expire_all()
        pin_set = db_session.scalar(
            select(PinSet)
            .where(
                PinSet.name == "My Fav Pins",
                PinSet.owner_id == subject_user.id,
            )
            .execution_options(include_pending=True)
        )
        assert pin_set is not None
        assert pin_set.owner_id == subject_user.id

    def test_guest_cannot_create_personal_set(self, anon_client):
        response = anon_client.post(
            "/user/me/sets", data={"name": "x"}, follow_redirects=False
        )
        assert response.status_code in (401, 403)

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_owner_can_delete_personal_set(
        self, auth_client_as_subject, db_session, subject_user
    ):
        pin_set = PersonalPinSetFactory(owner_id=subject_user.id)
        set_id = pin_set.id  # ty:ignore[unresolved-attribute]

        response = auth_client_as_subject.post(
            f"/user/sets/{set_id}/delete", follow_redirects=False
        )
        assert response.status_code == 303

        db_session.expire_all()
        # PersonalSet is not PendingMixin protected, regular delete is a hard delete.
        assert db_session.get(PinSet, set_id) is None

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_other_user_cannot_delete_someone_elses_set(
        self, auth_client_as_subject, db_session, other_editor_user
    ):
        pin_set = PersonalPinSetFactory(owner_id=other_editor_user.id)
        set_id = pin_set.id  # ty:ignore[unresolved-attribute]

        response = auth_client_as_subject.post(
            f"/user/sets/{set_id}/delete", follow_redirects=False
        )
        assert response.status_code == 403


@pytest.mark.integration
class TestPersonalSetMembership:
    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_add_pin_then_reorder(
        self, auth_client_as_subject, db_session, subject_user, admin_user
    ):
        pin_set = PersonalPinSetFactory(owner_id=subject_user.id)
        pin_one = PinFactory(approved=True, created_by=admin_user)
        pin_two = PinFactory(approved=True, created_by=admin_user)
        db_session.flush()
        set_id, id_one, id_two = pin_set.id, pin_one.id, pin_two.id  # ty:ignore[unresolved-attribute]

        r1 = auth_client_as_subject.post(
            f"/user/sets/{set_id}/pins/{id_one}", follow_redirects=False
        )
        r2 = auth_client_as_subject.post(
            f"/user/sets/{set_id}/pins/{id_two}", follow_redirects=False
        )
        assert r1.status_code in (200, 204)
        assert r2.status_code in (200, 204)

        db_session.expire_all()
        positions = dict(
            db_session.execute(
                select(
                    pin_set_memberships.c.pin_id, pin_set_memberships.c.position
                ).where(pin_set_memberships.c.set_id == set_id)
            ).all()
        )
        assert set(positions.keys()) == {id_one, id_two}
        assert positions[id_one] < positions[id_two]

        reorder = auth_client_as_subject.post(
            f"/user/sets/{set_id}/pins/reorder",
            data={"pin_ids": [id_two, id_one]},
            follow_redirects=False,
        )
        assert reorder.status_code in (200, 204, 303)

        db_session.expire_all()
        positions = dict(
            db_session.execute(
                select(
                    pin_set_memberships.c.pin_id, pin_set_memberships.c.position
                ).where(pin_set_memberships.c.set_id == set_id)
            ).all()
        )
        assert positions[id_two] < positions[id_one]


@pytest.mark.integration
class TestPromoteToGlobal:
    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_admin_can_promote_personal_set(
        self, admin_client, db_session, subject_user
    ):
        pin_set = PersonalPinSetFactory(owner_id=subject_user.id)
        set_id = pin_set.id  # ty:ignore[unresolved-attribute]

        response = admin_client.post(
            f"/user/sets/{set_id}/promote", follow_redirects=False
        )
        assert response.status_code in (200, 303)

        db_session.expire_all()
        refreshed = db_session.get(PinSet, set_id)
        assert refreshed is not None
        assert refreshed.owner_id is None

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_regular_user_cannot_promote(
        self, auth_client_as_subject, db_session, subject_user
    ):
        pin_set = PersonalPinSetFactory(owner_id=subject_user.id)
        response = auth_client_as_subject.post(
            f"/user/sets/{pin_set.id}/promote",  # ty:ignore[unresolved-attribute]
            follow_redirects=False,
        )
        assert response.status_code == 403
