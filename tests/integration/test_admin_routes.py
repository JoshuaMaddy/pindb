"""Integration tests for /admin/* smoke and /create/* role enforcement."""

import pytest

from tests.integration.helpers.authz import (
    assert_admin_only_post,
    assert_editor_or_admin_get,
)


@pytest.mark.integration
class TestAdminPanel:
    def test_admin_panel_requires_admin(self, client, auth_client, editor_client):
        """Editors are not admins — admin panel still blocks them."""
        assert client.get("/admin/").status_code == 401
        assert auth_client.get("/admin/").status_code == 403
        assert editor_client.get("/admin/").status_code == 403

    def test_admin_returns_200(self, admin_client):
        response = admin_client.get("/admin/")
        assert response.status_code == 200


@pytest.mark.integration
class TestAdminSearchSync:
    def test_search_sync_requires_admin(self, client, auth_client, editor_client):
        assert_admin_only_post("/admin/search/sync", client, auth_client, editor_client)

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
    def test_editor_or_admin_required(self, client, auth_client, path):
        assert_editor_or_admin_get(path, client, auth_client)

    @pytest.mark.parametrize("path", _CREATE_PATHS)
    def test_editor_returns_200(self, editor_client, path):
        response = editor_client.get(path)
        assert response.status_code == 200

    @pytest.mark.parametrize("path", _CREATE_PATHS)
    def test_admin_returns_200(self, admin_client, path):
        response = admin_client.get(path)
        assert response.status_code == 200
