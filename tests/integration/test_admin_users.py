"""`/admin/users/{id}/...` — grant/revoke admin and editor roles."""

from __future__ import annotations

import pytest

from pindb.database import User
from tests.fixtures.users import SUBJECT_USER_PARAMS


@pytest.mark.integration
class TestPromoteDemoteAdmin:
    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_admin_can_promote_user_to_admin(
        self, admin_client, db_session, subject_user
    ):
        response = admin_client.post(
            f"/admin/users/{subject_user.id}/promote", follow_redirects=False
        )
        assert response.status_code == 303

        db_session.expire_all()
        refreshed = db_session.get(User, subject_user.id)
        assert refreshed is not None and refreshed.is_admin is True

    def test_admin_can_demote_another_admin(
        self, admin_client, db_session, editor_user
    ):
        # Promote first, then demote.
        admin_client.post(
            f"/admin/users/{editor_user.id}/promote", follow_redirects=False
        )
        response = admin_client.post(
            f"/admin/users/{editor_user.id}/demote", follow_redirects=False
        )
        assert response.status_code == 303

        db_session.expire_all()
        refreshed = db_session.get(User, editor_user.id)
        assert refreshed is not None and refreshed.is_admin is False

    def test_admin_cannot_demote_self(self, admin_client, admin_user, db_session):
        response = admin_client.post(
            f"/admin/users/{admin_user.id}/demote", follow_redirects=False
        )
        assert response.status_code == 400

        db_session.expire_all()
        refreshed = db_session.get(User, admin_user.id)
        assert refreshed is not None and refreshed.is_admin is True


@pytest.mark.integration
class TestPromoteDemoteEditor:
    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_admin_can_promote_user_to_editor(
        self, admin_client, db_session, subject_user
    ):
        response = admin_client.post(
            f"/admin/users/{subject_user.id}/promote-editor", follow_redirects=False
        )
        assert response.status_code == 303

        db_session.expire_all()
        refreshed = db_session.get(User, subject_user.id)
        assert refreshed is not None and refreshed.is_editor is True

    def test_admin_can_demote_editor(self, admin_client, db_session, editor_user):
        response = admin_client.post(
            f"/admin/users/{editor_user.id}/demote-editor", follow_redirects=False
        )
        assert response.status_code == 303

        db_session.expire_all()
        refreshed = db_session.get(User, editor_user.id)
        assert refreshed is not None and refreshed.is_editor is False


@pytest.mark.integration
class TestAuthorization:
    @pytest.mark.parametrize(
        "suffix",
        ["promote", "demote", "promote-editor", "demote-editor"],
    )
    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_non_admin_rejected(self, auth_client_as_subject, subject_user, suffix):
        response = auth_client_as_subject.post(
            f"/admin/users/{subject_user.id}/{suffix}", follow_redirects=False
        )
        assert response.status_code == 403

    @pytest.mark.parametrize(
        "suffix",
        ["promote", "demote", "promote-editor", "demote-editor"],
    )
    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_editor_rejected(self, editor_client, subject_user, suffix):
        response = editor_client.post(
            f"/admin/users/{subject_user.id}/{suffix}", follow_redirects=False
        )
        assert response.status_code == 403


@pytest.mark.integration
class TestMissingUser:
    def test_promote_unknown_user_returns_404(self, admin_client):
        response = admin_client.post(
            "/admin/users/9999999/promote", follow_redirects=False
        )
        assert response.status_code == 404
