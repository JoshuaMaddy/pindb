"""Integration tests for /admin/* routes — auth enforcement and basic access."""

import pytest


@pytest.mark.integration
class TestAdminPanel:
    def test_unauthenticated_returns_401(self, client):
        response = client.get("/admin/")
        assert response.status_code == 401

    def test_non_admin_returns_403(self, auth_client):
        response = auth_client.get("/admin/")
        assert response.status_code == 403

    def test_admin_returns_200(self, admin_client):
        response = admin_client.get("/admin/")
        assert response.status_code == 200


@pytest.mark.integration
class TestAdminSearchSync:
    def test_unauthenticated_returns_401(self, client):
        response = client.post("/admin/search/sync")
        assert response.status_code == 401

    def test_non_admin_returns_403(self, auth_client):
        response = auth_client.post("/admin/search/sync")
        assert response.status_code == 403

    def test_admin_triggers_sync(self, admin_client, patch_meilisearch):
        response = admin_client.post("/admin/search/sync")
        # Should succeed (200 or redirect)
        assert response.status_code in (200, 302, 303)


@pytest.mark.integration
class TestCreateRouteAuthEnforcement:
    """Verify the /create/* router enforces admin-only access."""

    @pytest.mark.parametrize(
        "path",
        [
            "/create/",
            "/create/artist",
            "/create/shop",
            "/create/material",
            "/create/tag",
        ],
    )
    def test_unauthenticated_returns_401(self, client, path):
        response = client.get(path)
        assert response.status_code == 401

    @pytest.mark.parametrize(
        "path",
        [
            "/create/",
            "/create/artist",
            "/create/shop",
            "/create/material",
            "/create/tag",
        ],
    )
    def test_non_admin_returns_403(self, auth_client, path):
        response = auth_client.get(path)
        assert response.status_code == 403

    @pytest.mark.parametrize(
        "path",
        [
            "/create/",
            "/create/artist",
            "/create/shop",
            "/create/material",
            "/create/tag",
        ],
    )
    def test_admin_returns_200(self, admin_client, path):
        response = admin_client.get(path)
        assert response.status_code == 200
