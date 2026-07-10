"""Bulk import columns dropdown (part of the bulk-import island): toggle + persist."""

from __future__ import annotations

import json

from playwright.sync_api import expect


def _open_menu(page):
    trigger = page.get_by_role("button", name="Toggle columns")
    trigger.click()
    return page.locator("label", has=page.locator(".col-toggle-check"))


class TestBulkColumnsDropdown:
    def test_open_toggle_close(self, admin_browser_context, live_server):
        page = admin_browser_context.new_page()
        page.goto(f"{live_server}/bulk/pin", wait_until="networkidle")

        labels = _open_menu(page)
        expect(labels.first).to_be_visible()
        assert labels.count() >= 10  # all optional columns listed

        # Click-outside closes the panel.
        page.locator("h1", has_text="Bulk Import Pins").click()
        expect(labels.first).not_to_be_visible()

    def test_toggle_hides_column_including_new_rows_and_persists(
        self, admin_browser_context, live_server
    ):
        page = admin_browser_context.new_page()
        page.goto(f"{live_server}/bulk/pin", wait_until="networkidle")
        page.evaluate("localStorage.removeItem('bulk_visible_cols')")
        page.reload(wait_until="networkidle")

        artists_header = page.locator('th[data-col="artists"]')
        expect(artists_header).to_be_visible()

        _open_menu(page)
        page.locator('input.col-toggle-check[data-col="artists"]').uncheck()
        expect(artists_header).not_to_be_visible()

        # New rows must respect the current column visibility.
        page.locator("#add-row-btn").click()
        new_row_cell = page.locator('#bulk-tbody td[data-col="artists"]').last
        expect(new_row_cell).not_to_be_visible()

        # Persists across reload (localStorage).
        page.reload(wait_until="networkidle")
        expect(page.locator('th[data-col="artists"]')).not_to_be_visible()

        saved = page.evaluate("localStorage.getItem('bulk_visible_cols')")
        assert json.loads(saved) == {"artists": False}

        page.evaluate("localStorage.removeItem('bulk_visible_cols')")

    def test_menu_visual_baseline(
        self, admin_browser_context, live_server, assert_screenshot
    ):
        page = admin_browser_context.new_page()
        page.goto(f"{live_server}/bulk/pin", wait_until="networkidle")
        page.evaluate("localStorage.removeItem('bulk_visible_cols')")
        page.reload(wait_until="networkidle")

        labels = _open_menu(page)
        expect(labels.first).to_be_visible()
        # Capture the panel itself — it's absolutely positioned, so a shot of
        # the island root would clip it away.
        assert_screenshot(
            page.locator("[data-dropdown-panel]"),
            "bulk-columns-menu-open",
        )
