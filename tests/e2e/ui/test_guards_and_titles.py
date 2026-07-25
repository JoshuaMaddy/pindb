"""Anonymous/editor guards and document titles (httpx)."""

from __future__ import annotations

import pytest

from tests.e2e.ui.http import parse_html as _soup


class TestAuthGuards:
    def test_anonymous_get_create_shop_is_forbidden(self, anon_http_client):
        response = anon_http_client.get("/create/shop")
        assert response.status_code in (401, 403)

    def test_anonymous_admin_panel_is_forbidden(self, anon_http_client):
        response = anon_http_client.get("/admin")
        assert response.status_code in (401, 403)

    def test_anonymous_catalog_pages_are_forbidden(self, anon_http_client):
        """The gate, end to end: catalog pages used to be public."""
        for path in ("/", "/list/shops", "/search/pin", "/docs", "/about"):
            assert anon_http_client.get(path).status_code == 401, path

    def test_editor_admin_panel_is_forbidden(self, editor_http_client):
        response = editor_http_client.get("/admin")
        assert response.status_code == 403


class TestPageTitles:
    def test_login_page_title(self, anon_http_client):
        response = anon_http_client.get("/auth/login")
        assert response.status_code == 200
        soup = _soup(response)
        assert soup.title is not None
        assert soup.title.string == "Login | PinDB"

    @pytest.mark.parametrize(
        ("path", "expected_title"),
        [
            ("/", "Home | PinDB"),
            ("/list/shops", "Shops | PinDB"),
            ("/search/pin", "Search for a Pin | PinDB"),
        ],
    )
    def test_top_level_pages_have_expected_titles(
        self, admin_http_client, path, expected_title
    ):
        response = admin_http_client.get(path)
        assert response.status_code == 200
        soup = _soup(response)
        assert soup.title is not None
        assert soup.title.string == expected_title

    def test_admin_pending_queue_title_for_admin(self, admin_http_client):
        response = admin_http_client.get("/admin/pending")
        assert response.status_code == 200
        soup = _soup(response)
        assert soup.title is not None
        assert soup.title.string == "Pending Approvals | PinDB"
