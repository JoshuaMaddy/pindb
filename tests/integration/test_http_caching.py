"""``Cache-Control`` for ``/static`` (vendored + main.css) and path helper coverage.

Uses the same integration stack as other route tests: Postgres via testcontainers
(Docker), real ``pindb`` app, and the ``client`` TestClient.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pindb.http_caching import (
    VENDORED_STATIC_CACHE_CONTROL,
    is_vendored_or_built_css_path,
)


@pytest.mark.integration
class TestVendoredPathHelper:
    @pytest.fixture(autouse=True)
    def _use_app(self, client) -> None:
        """Ensure the Postgres testcontainer and full app are active (same as HTTP tests)."""

    def test_detects_vendor_and_main_css(self) -> None:
        assert is_vendored_or_built_css_path("/x/static/vendor/foo.js")
        assert is_vendored_or_built_css_path("vendor/foo.js")
        assert is_vendored_or_built_css_path("/abs/path/to/main.css")
        assert not is_vendored_or_built_css_path(Path("/static/input.css"))
        assert not is_vendored_or_built_css_path(Path("/static/favicon.png"))


@pytest.mark.integration
class TestCacheBustedStaticFiles:
    def test_vendored_js_is_long_cache(self, client):
        r = client.get("/static/vendor/htmx.min.js", follow_redirects=False)
        assert r.status_code == 200
        assert r.headers["cache-control"] == VENDORED_STATIC_CACHE_CONTROL

    def test_main_css_is_long_cache(self, client):
        r = client.get("/static/main.css", follow_redirects=False)
        assert r.status_code == 200
        assert r.headers["cache-control"] == VENDORED_STATIC_CACHE_CONTROL

    def test_unbusted_input_css_is_not_vendored_policy(self, client):
        r = client.get("/static/input.css", follow_redirects=False)
        assert r.status_code == 200
        assert r.headers.get("cache-control") != VENDORED_STATIC_CACHE_CONTROL
