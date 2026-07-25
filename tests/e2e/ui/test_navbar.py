"""Navbar links and role-gated affordances (httpx)."""

from __future__ import annotations

from tests.e2e.ui.http import parse_html as _soup


class TestNavbar:
    def test_anonymous_cannot_reach_the_homepage_at_all(self, anon_http_client):
        """There is no anonymous navbar any more — there is no anonymous page."""
        assert anon_http_client.get("/").status_code == 401

    def test_regular_member_navbar_hides_create_and_admin(self, regular_http_client):
        response = regular_http_client.get("/")
        assert response.status_code == 200
        soup = _soup(response)
        assert soup.select_one('a:-soup-contains("PinDB")') is not None
        assert soup.select_one('nav a[href="/create"]') is None
        assert soup.select_one('nav a[href="/admin"]') is None

    def test_admin_navbar_shows_create_and_admin(self, admin_http_client):
        response = admin_http_client.get("/")
        assert response.status_code == 200
        soup = _soup(response)
        assert soup.select_one('nav a[href="/create"]') is not None
        assert soup.select_one('nav a[href="/admin"]') is not None
        assert soup.select_one('form[action="/auth/logout"]') is not None
        assert soup.select_one('nav a[href^="/user/"]') is not None

    def test_editor_navbar_shows_create_but_not_admin(self, editor_http_client):
        response = editor_http_client.get("/")
        assert response.status_code == 200
        soup = _soup(response)
        assert soup.select_one('nav a[href="/create"]') is not None
        assert soup.select_one('nav a[href="/admin"]') is None
