"""Integration tests for /user/{username} profile pages."""

import pytest


@pytest.mark.integration
class TestUserProfile:
    def test_existing_user_profile_returns_200(self, client, test_user):
        response = client.get(f"/user/{test_user.username}")
        assert response.status_code == 200

    def test_profile_shows_username(self, client, test_user):
        response = client.get(f"/user/{test_user.username}")
        assert test_user.username in response.text

    def test_nonexistent_user_returns_404(self, client):
        response = client.get("/user/definitely_does_not_exist_xyz")
        assert response.status_code == 404

    def test_authenticated_user_viewing_own_profile(self, auth_client, test_user):
        response = auth_client.get(f"/user/{test_user.username}")
        assert response.status_code == 200


@pytest.mark.integration
class TestUserFavoritesPage:
    def test_favorites_page_returns_200(self, client, test_user):
        response = client.get(f"/user/{test_user.username}/favorites")
        assert response.status_code == 200

    def test_favorites_empty_state(self, client, test_user):
        response = client.get(f"/user/{test_user.username}/favorites")
        assert response.status_code == 200


@pytest.mark.integration
class TestUserCollectionPage:
    def test_collection_page_returns_200(self, client, test_user):
        response = client.get(f"/user/{test_user.username}/collection")
        assert response.status_code == 200

    def test_wants_page_returns_200(self, client, test_user):
        response = client.get(f"/user/{test_user.username}/wants")
        assert response.status_code == 200

    def test_trades_page_returns_200(self, client, test_user):
        response = client.get(f"/user/{test_user.username}/trades")
        assert response.status_code == 200
