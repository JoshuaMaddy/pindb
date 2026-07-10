"""Bulk tag entry: behavior contract for the vanilla → Svelte island port.

Written against legacy ``bulk/bulk_tag.js`` first (lockstep protocol); must
pass unchanged after the port. Stable contract: ``#bulk-tag-add-row`` /
``#bulk-tag-submit`` / ``#bulk-tag-submit-label``, ``.bulk-data-row`` rows in
``#bulk-tag-tbody``, first text input per row = name, first multi-select =
implications ("Child of"), ``.row-error`` + title, success modal ids,
cross-row option broadcasting, name normalization (lowercase, spaces → _).
"""

from __future__ import annotations

from playwright.sync_api import expect

from tests.e2e.select_helpers import multi_add


def _goto(page, live_server) -> None:
    page.goto(f"{live_server}/bulk/tag", wait_until="networkidle")
    expect(page.locator("#bulk-tag-tbody .bulk-data-row")).to_have_count(2)


def _name_input(page, row_index: int):
    return (
        page.locator("#bulk-tag-tbody .bulk-data-row")
        .nth(row_index)
        .locator('input[type="text"]')
        .first
    )


def _implications_select(page, row_index: int):
    return (
        page.locator("#bulk-tag-tbody .bulk-data-row")
        .nth(row_index)
        .locator("select[multiple]")
        .first
    )


class TestBulkTag:
    def test_cross_row_broadcast_and_submit_roundtrip(
        self, editor_browser_context, live_server, db_handle
    ):
        page = editor_browser_context.new_page()
        _goto(page, live_server)

        # Names normalize live: lowercase, spaces to underscores.
        _name_input(page, 0).fill("Bulk Tag Alpha")
        _name_input(page, 1).fill("bulk_tag_beta")

        # Row 0's (normalized) name is broadcast into row 1's implications —
        # multi_add waits for the option to appear before picking it.
        multi_add(page, _implications_select(page, 1), "bulk_tag_alpha")

        with page.expect_response(
            lambda r: r.request.method == "POST" and r.url.endswith("/bulk/tag")
        ) as response_info:
            page.locator("#bulk-tag-submit").click()
        assert response_info.value.status == 200
        payload = response_info.value.json()
        assert payload["created_count"] == 2
        assert payload["failed_count"] == 0

        expect(page.locator("#bulk-tag-success-modal")).to_be_visible()
        expect(page.locator("#bulk-tag-modal-grid a")).to_have_count(2)
        # Successful rows leave the table; an empty table gets one fresh row.
        expect(page.locator("#bulk-tag-tbody .bulk-data-row")).to_have_count(1)

        rows = db_handle(
            "SELECT name, approved_at IS NULL FROM tags "
            "WHERE name IN ('bulk_tag_alpha', 'bulk_tag_beta') ORDER BY name",
        )
        assert [(name, pending) for name, pending in rows] == [
            ("bulk_tag_alpha", True),  # editor submission lands pending
            ("bulk_tag_beta", True),
        ]
        implication = db_handle(
            """SELECT p.name FROM tag_implications ti
               JOIN tags c ON c.id = ti.tag_id
               JOIN tags p ON p.id = ti.implied_tag_id
               WHERE c.name = 'bulk_tag_beta'"""
        )
        assert [name for (name,) in implication] == ["bulk_tag_alpha"]

    def test_duplicate_names_block_submit(self, editor_browser_context, live_server):
        page = editor_browser_context.new_page()
        _goto(page, live_server)
        _name_input(page, 0).fill("dupe_tag")
        _name_input(page, 1).fill("dupe_tag")

        page.locator("#bulk-tag-submit").click()
        page.wait_for_function(
            """() => document.querySelectorAll(
                '#bulk-tag-tbody .bulk-data-row.row-error').length === 2"""
        )
        title = (
            page.locator("#bulk-tag-tbody .bulk-data-row").nth(1).get_attribute("title")
        )
        assert "duplicate" in (title or "").lower()

    def test_add_dup_delete_rows_update_label(
        self, editor_browser_context, live_server
    ):
        page = editor_browser_context.new_page()
        _goto(page, live_server)
        expect(page.locator("#bulk-tag-submit-label")).to_have_text("Submit (2)")

        page.locator("#bulk-tag-add-row").click()
        expect(page.locator("#bulk-tag-submit-label")).to_have_text("Submit (3)")

        page.locator(".del-btn").last.click()
        expect(page.locator("#bulk-tag-submit-label")).to_have_text("Submit (2)")

        page.locator(".dup-btn").first.click()
        expect(page.locator("#bulk-tag-submit-label")).to_have_text("Submit (3)")

    def test_grid_visual_baseline(
        self, editor_browser_context, live_server, assert_screenshot
    ):
        page = editor_browser_context.new_page()
        _goto(page, live_server)
        assert_screenshot(
            page.locator("table.bulk-tag-table"),
            "bulk-tag-grid-two-rows",
        )
