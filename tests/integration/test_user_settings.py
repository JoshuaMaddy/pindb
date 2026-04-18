"""`POST /user/me/settings` — updates User.theme with whitelist validation."""

from __future__ import annotations

import pytest

from pindb.database import User


@pytest.mark.integration
class TestUpdateUserSettings:
    def test_valid_theme_is_persisted(self, auth_client, db_session, test_user):
        response = auth_client.post("/user/me/settings", data={"theme": "dracula"})
        assert response.status_code == 204

        db_session.expire_all()
        refreshed = db_session.get(User, test_user.id)
        assert refreshed is not None
        assert refreshed.theme == "dracula"

    def test_invalid_theme_rejected(self, auth_client, db_session, test_user):
        original = test_user.theme
        response = auth_client.post(
            "/user/me/settings", data={"theme": "not-a-real-theme"}
        )
        assert response.status_code == 422

        db_session.expire_all()
        refreshed = db_session.get(User, test_user.id)
        assert refreshed is not None
        assert refreshed.theme == original

    def test_guest_rejected(self, anon_client):
        response = anon_client.post("/user/me/settings", data={"theme": "dracula"})
        assert response.status_code in (401, 403)

    def test_missing_theme_field_is_422(self, auth_client):
        response = auth_client.post("/user/me/settings", data={})
        assert response.status_code == 422


@pytest.mark.integration
class TestDeleteOwnAccount:
    def test_deletes_user_and_clears_cookie(self, auth_client, db_session, test_user):
        user_id: int = test_user.id
        response = auth_client.post(
            "/user/me/delete-account",
            data={"confirm_username": test_user.username},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers.get("location") == "/"
        set_cookie = response.headers.get("set-cookie", "").lower()
        assert "session" in set_cookie and (
            "max-age=0" in set_cookie or "expires=" in set_cookie
        )

        db_session.expire_all()
        assert db_session.get(User, user_id) is None

    def test_wrong_username_rejected(self, auth_client, db_session, test_user):
        response = auth_client.post(
            "/user/me/delete-account",
            data={"confirm_username": "not_the_username"},
            follow_redirects=False,
        )
        assert response.status_code == 400

        db_session.expire_all()
        assert db_session.get(User, test_user.id) is not None

    def test_guest_rejected(self, anon_client):
        response = anon_client.post(
            "/user/me/delete-account",
            data={"confirm_username": "anyone"},
            follow_redirects=False,
        )
        assert response.status_code in (401, 403)
