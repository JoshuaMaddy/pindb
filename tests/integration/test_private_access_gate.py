"""The default-deny auth gate: what an anonymous visitor can and cannot reach.

PinDB is a private community. The only page an anonymous visitor may see is the
login page, so these tests are the regression net for the whole lockdown — if
one of them starts failing open, catalog data is public again.
"""

from __future__ import annotations

import pytest
from starlette.routing import Mount
from starlette.routing import Route as StarletteRoute

from pindb import app
from pindb.require_login import PUBLIC_EXACT, PUBLIC_PREFIXES, is_public_path

# Paths an anonymous visitor must not reach. Spans every content area: the
# homepage, list and search pages, entity detail pages, per-user pages, images,
# docs and legal.
MEMBERS_ONLY_PATHS = [
    "/",
    "/list/",
    "/list/tags",
    "/list/shops",
    "/search/pin",
    "/docs",
    "/about",
    "/privacy",
    "/terms",
    "/get/tag-options",
    "/messages",
    "/admin",
]


@pytest.mark.integration
class TestAnonymousIsDenied:
    @pytest.mark.parametrize("path", MEMBERS_ONLY_PATHS)
    def test_returns_401(self, anon_client, path):
        assert anon_client.get(path, follow_redirects=False).status_code == 401

    def test_user_pages_are_denied(self, anon_client, test_user):
        for suffix in (
            "",
            "/favorites",
            "/collection",
            "/wants",
            "/trades",
            "/display",
        ):
            path = f"/user/{test_user.username}{suffix}"
            assert anon_client.get(path, follow_redirects=False).status_code == 401

    def test_image_bytes_are_denied(self, anon_client):
        response = anon_client.get(
            "/get/image/00000000-0000-0000-0000-000000000000",
            follow_redirects=False,
        )
        # 401 from the gate, never 404 — the gate runs before routing, so an
        # anonymous visitor cannot even probe which guids exist.
        assert response.status_code == 401

    def test_og_image_route_is_gone(self, anon_client, auth_client):
        assert anon_client.get("/get/og-image/pin/1").status_code == 401
        assert auth_client.get("/get/og-image/pin/1").status_code == 404


@pytest.mark.integration
class TestMembersAreAllowed:
    @pytest.mark.parametrize("path", ["/", "/list/", "/list/tags", "/docs"])
    def test_returns_200(self, auth_client, path):
        assert auth_client.get(path, follow_redirects=False).status_code == 200


@pytest.mark.integration
class TestPublicAllowlist:
    @pytest.mark.parametrize("path", ["/healthz", "/auth/login", "/robots.txt"])
    def test_reachable_anonymously(self, anon_client, path):
        assert anon_client.get(path, follow_redirects=False).status_code == 200

    def test_robots_denies_everything(self, anon_client):
        body = anon_client.get("/robots.txt").text
        assert "User-agent: *" in body
        assert "Disallow: /" in body

    def test_editor_docs_are_not_served_as_static_files(self, anon_client, auth_client):
        """The markdown lives outside ``static/`` precisely so the mount, which
        the gate must allowlist for the login page's CSS, cannot serve it."""
        path = "/static/docs/editors/5_pin_creation_guidance.md"
        assert anon_client.get(path).status_code == 404
        assert auth_client.get(path).status_code == 404


@pytest.mark.integration
class TestRejectionShape:
    def test_browser_navigation_redirects_to_login(self, anon_client):
        response = anon_client.get(
            "/list/tags",
            headers={"Accept": "text/html"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/auth/login?next=%2Flist%2Ftags"

    def test_query_string_is_preserved_in_next(self, anon_client):
        response = anon_client.get(
            "/list/tags?page=3",
            headers={"Accept": "text/html"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert (
            response.headers["location"] == "/auth/login?next=%2Flist%2Ftags%3Fpage%3D3"
        )

    def test_htmx_request_gets_hx_redirect(self, anon_client):
        response = anon_client.get(
            "/list/tags",
            headers={"HX-Request": "true"},
            follow_redirects=False,
        )
        assert response.status_code == 401
        assert response.headers["HX-Redirect"] == "/auth/login"

    def test_non_html_accept_gets_plain_401(self, anon_client):
        response = anon_client.get("/list/tags", follow_redirects=False)
        assert response.status_code == 401
        assert "location" not in response.headers


@pytest.mark.integration
class TestNoIndexHeaders:
    def test_every_response_carries_noindex(self, anon_client, auth_client):
        for response in (
            anon_client.get("/auth/login"),
            auth_client.get("/"),
            auth_client.get("/list/tags"),
        ):
            assert "noindex" in response.headers["X-Robots-Tag"]

    def test_pages_emit_no_opengraph_tags(self, auth_client, test_user):
        for path in ("/", "/list/tags", f"/user/{test_user.username}"):
            body = auth_client.get(path).text
            assert 'property="og:' not in body
            assert 'name="twitter:' not in body
            assert 'rel="canonical"' not in body


@pytest.mark.integration
class TestNoRouteIsAccidentallyPublic:
    """Fail-safe: a route added later is private unless someone edits the
    allowlist, and editing the allowlist is what this test makes visible."""

    def test_every_route_is_gated_or_allowlisted(self, anon_client):
        offenders: list[str] = []
        for route in app.routes:
            if isinstance(route, Mount):
                continue
            if not isinstance(route, StarletteRoute):
                continue
            path = route.path
            # Skip parameterised paths: they cannot be requested literally, and
            # the gate runs before routing so the shape is irrelevant to it.
            if "{" in path:
                continue
            if is_public_path(path):
                continue
            if "GET" not in (route.methods or set()):
                continue
            if anon_client.get(path, follow_redirects=False).status_code != 401:
                offenders.append(path)
        assert offenders == [], f"routes reachable anonymously: {offenders}"

    def test_allowlist_is_the_expected_short_list(self):
        assert PUBLIC_EXACT == {
            "/healthz",
            "/auth/login",
            "/auth/logout",
            "/robots.txt",
            "/favicon.ico",
        }
        assert PUBLIC_PREFIXES == ("/static/", "/templates-js/")
