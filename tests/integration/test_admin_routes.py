"""Integration tests for /admin/* routes and /create/* role enforcement."""

import pytest


@pytest.mark.integration
class TestAdminPanel:
    def test_unauthenticated_returns_401(self, client):
        response = client.get("/admin/")
        assert response.status_code == 401

    def test_non_admin_returns_403(self, auth_client):
        response = auth_client.get("/admin/")
        assert response.status_code == 403

    def test_editor_returns_403(self, editor_client):
        """Editors are not admins — admin panel still blocks them."""
        response = editor_client.get("/admin/")
        assert response.status_code == 403

    def test_admin_returns_200(self, admin_client):
        response = admin_client.get("/admin/")
        assert response.status_code == 200


@pytest.mark.integration
class TestAdminBulkTagsPage:
    def test_unauthenticated_returns_401(self, client):
        response = client.get("/admin/tags/bulk")
        assert response.status_code == 401

    def test_non_admin_returns_403(self, auth_client):
        response = auth_client.get("/admin/tags/bulk")
        assert response.status_code == 403

    def test_admin_returns_200(self, admin_client):
        response = admin_client.get("/admin/tags/bulk")
        assert response.status_code == 200
        assert "Bulk tags" in response.text


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
        assert response.status_code in (200, 302, 303)


_CREATE_PATHS = [
    "/create/",
    "/create/artist",
    "/create/shop",
    "/create/tag",
    "/create/pin_set",
]


@pytest.mark.integration
class TestCreateRouteAuthEnforcement:
    """`/create/*` is gated by the `editor` dependency: editor or admin."""

    @pytest.mark.parametrize("path", _CREATE_PATHS)
    def test_unauthenticated_returns_401(self, client, path):
        response = client.get(path)
        assert response.status_code == 401

    @pytest.mark.parametrize("path", _CREATE_PATHS)
    def test_regular_user_returns_403(self, auth_client, path):
        response = auth_client.get(path)
        assert response.status_code == 403

    @pytest.mark.parametrize("path", _CREATE_PATHS)
    def test_editor_returns_200(self, editor_client, path):
        response = editor_client.get(path)
        assert response.status_code == 200

    @pytest.mark.parametrize("path", _CREATE_PATHS)
    def test_admin_returns_200(self, admin_client, path):
        response = admin_client.get(path)
        assert response.status_code == 200
