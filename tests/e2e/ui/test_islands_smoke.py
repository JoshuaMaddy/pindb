"""Svelte island infrastructure smoke: loader served, cached, mounts cleanly."""

from __future__ import annotations

import httpx


class TestIslandsInfra:
    def test_mount_js_served_immutable(self, live_server):
        response = httpx.get(f"{live_server}/static/islands/mount.js?v=test")
        assert response.status_code == 200
        assert "immutable" in response.headers.get("cache-control", "")
        assert "data-island" in response.text

    def test_island_bundle_served_immutable(self, live_server):
        response = httpx.get(f"{live_server}/static/islands/bulk-import.js?v=test")
        assert response.status_code == 200
        assert "immutable" in response.headers.get("cache-control", "")

    def test_bulk_page_mounts_island_without_console_errors(
        self, admin_browser_context, live_server
    ):
        page = admin_browser_context.new_page()
        errors: list[str] = []
        page.on(
            "console",
            lambda message: (
                errors.append(message.text) if message.type == "error" else None
            ),
        )
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(f"{live_server}/bulk/pin", wait_until="networkidle")

        # Errors first — they carry the root cause when mounting fails.
        assert errors == [], f"console errors on bulk import page: {errors}"

        # Island replaced its props script with rendered content.
        island = page.locator('[data-island="bulk-import"]')
        assert island.count() == 1
        assert island.locator("#add-row-btn").count() == 1
