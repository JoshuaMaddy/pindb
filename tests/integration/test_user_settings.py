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
