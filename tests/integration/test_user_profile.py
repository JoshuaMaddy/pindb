"""Integration tests for /user/{username} profile pages."""

import pytest

from tests.fixtures.users import (
    MINIMAL_USER_USERNAME,
    SUBJECT_USER_PARAMS,
)


@pytest.mark.integration
class TestUserProfile:
    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_existing_user_profile_returns_200(self, client, subject_user):
        response = client.get(f"/user/{subject_user.username}")
        assert response.status_code == 200

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_profile_shows_username(self, client, subject_user):
        response = client.get(f"/user/{subject_user.username}")
        assert subject_user.username in response.text

    def test_nonexistent_user_returns_404(self, client):
        response = client.get("/user/definitely_does_not_exist_xyz")
        assert response.status_code == 404

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_authenticated_user_viewing_own_profile(
        self, auth_client_as_subject, subject_user
    ):
        response = auth_client_as_subject.get(f"/user/{subject_user.username}")
        assert response.status_code == 200


@pytest.mark.integration
class TestUserFavoritesPage:
    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_favorites_page_returns_200(self, client, subject_user):
        response = client.get(f"/user/{subject_user.username}/favorites")
        assert response.status_code == 200

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_favorites_empty_or_populated(self, client, subject_user):
        response = client.get(f"/user/{subject_user.username}/favorites")
        assert response.status_code == 200
        if subject_user.username == MINIMAL_USER_USERNAME:
            assert "No pins in favorites yet." in response.text
        else:
            assert "No pins in favorites yet." not in response.text
            assert "FullProf Alpha" in response.text


@pytest.mark.integration
class TestUserCollectionPage:
    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_collection_page_returns_200(self, client, subject_user):
        response = client.get(f"/user/{subject_user.username}/collection")
        assert response.status_code == 200

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_wants_page_returns_200(self, client, subject_user):
        response = client.get(f"/user/{subject_user.username}/wants")
        assert response.status_code == 200

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_trades_page_returns_200(self, client, subject_user):
        response = client.get(f"/user/{subject_user.username}/trades")
        assert response.status_code == 200
