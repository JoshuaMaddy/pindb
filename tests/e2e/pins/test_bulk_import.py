"""Bulk pin import: behavior contract for the vanilla → Svelte island rewrite.

Written against the legacy ``bulk/bulk_import.js`` first (lockstep protocol);
must pass unchanged after the island rewrite. Stable contract used here:
``#add-row-btn`` / ``#submit-btn`` / ``#submit-label``, ``.bulk-data-row``
rows, ``input[data-field="name"]``, ``td[data-col-type=...] select`` driven
through the shared select widget helpers, ``.img-file-input[data-side]``,
grades toggle button + ``.grades-count`` badge, ``.row-error``,
``#success-modal`` grid, column copy/paste buttons, sessionStorage draft key
``bulk_persist``.
"""

from __future__ import annotations

from playwright.sync_api import expect

from tests.e2e.select_helpers import (
    expect_option_available,
    multi_add,
    single_pick,
)
from tests.helpers.binary_fixtures import tiny_png_bytes


def _goto_bulk(page, live_server) -> None:
    page.goto(f"{live_server}/bulk/pin", wait_until="networkidle")
    expect(page.locator(".bulk-data-row")).to_have_count(1)


def _row(page, index: int):
    return page.locator(".bulk-data-row").nth(index)


def _fill_name(page, row_index: int, name: str) -> None:
    _row(page, row_index).locator('input[data-field="name"]').fill(name)


def _upload_front(page, row_index: int) -> None:
    _row(page, row_index).locator('.img-file-input[data-side="front"]').set_input_files(
        [{"name": "f.png", "mimeType": "image/png", "buffer": tiny_png_bytes()}]
    )
    # Wait for the upload round-trip: the drop cell gets a background preview.
    page.wait_for_function(
        """(idx) => {
            const row = document.querySelectorAll('.bulk-data-row')[idx];
            const cell = row.querySelector('.image-drop-cell[data-side="front"]');
            return (cell.style.backgroundImage || '').includes('url(');
        }""",
        arg=row_index,
        timeout=15_000,
    )


def _cell_select(page, row_index: int, col_type: str):
    return _row(page, row_index).locator(f'td[data-col-type="{col_type}"] select')


def _ts_create(page, row_index: int, col_type: str, value: str) -> None:
    """Create + select a new option in a multi-select cell via the UI."""
    multi_add(page, _cell_select(page, row_index, col_type), value, create=True)


def _ts_set_single(page, row_index: int, col_type: str, option_text: str) -> None:
    single_pick(page, _cell_select(page, row_index, col_type), option_text)


class TestBulkImport:
    def test_full_submit_roundtrip(self, admin_browser_context, live_server, db_handle):
        page = admin_browser_context.new_page()
        _goto_bulk(page, live_server)
        expect(page.locator("#submit-label")).to_have_text("Submit (1)")

        _fill_name(page, 0, "BulkPinOne")
        _upload_front(page, 0)
        _ts_set_single(page, 0, "acquisition_type", "Single")
        _ts_create(page, 0, "shops", "BulkShopNew")
        _ts_create(page, 0, "tags", "bulk-tag-new")

        with page.expect_response(
            lambda r: r.request.method == "POST" and r.url.endswith("/bulk/pin")
        ) as response_info:
            page.locator("#submit-btn").click()
        assert response_info.value.status == 200
        payload = response_info.value.json()
        assert payload["created_count"] == 1
        assert payload["failed_count"] == 0

        expect(page.locator("#success-modal")).to_be_visible()
        cards = page.locator("#modal-grid a")
        expect(cards).to_have_count(1)
        # Successful rows leave the table.
        expect(page.locator(".bulk-data-row")).to_have_count(0)

        rows = db_handle(
            "SELECT front_image_guid IS NOT NULL FROM pins WHERE name = %s",
            ("BulkPinOne",),
        )
        assert rows and rows[0][0] is True
        shop = db_handle("SELECT id FROM shops WHERE name = %s", ("BulkShopNew",))
        assert shop
        tag = db_handle("SELECT id FROM tags WHERE name = %s", ("bulk-tag-new",))
        assert tag

    def test_validation_blocks_and_highlights_row(
        self, admin_browser_context, live_server
    ):
        page = admin_browser_context.new_page()
        _goto_bulk(page, live_server)
        _fill_name(page, 0, "NoImagePin")
        _ts_set_single(page, 0, "acquisition_type", "Single")

        page.locator("#submit-btn").click()
        # Client validation blocks the request; the row is flagged.
        page.wait_for_function(
            "document.querySelector('.bulk-data-row').classList.contains('row-error')"
        )
        title = _row(page, 0).get_attribute("title") or ""
        assert "image" in title.lower()

    def test_cross_row_created_option_available(
        self, admin_browser_context, live_server
    ):
        page = admin_browser_context.new_page()
        _goto_bulk(page, live_server)
        page.locator("#add-row-btn").click()
        expect(page.locator(".bulk-data-row")).to_have_count(2)

        _ts_create(page, 0, "shops", "SharedShopOpt")
        # The created option is broadcast to the other row's picker.
        expect_option_available(page, _cell_select(page, 1, "shops"), "SharedShopOpt")

    def test_grades_subrow_edit_updates_badge(self, admin_browser_context, live_server):
        page = admin_browser_context.new_page()
        _goto_bulk(page, live_server)

        expect(page.locator(".grades-count").first).to_have_text("1")
        page.locator(".grades-toggle-btn").first.click()
        sub_inputs = page.locator(
            '.grades-sub-row input[type="text"], .grades-sub-row input[placeholder="Grade"]'
        )
        expect(sub_inputs.first).to_be_visible()

        page.get_by_role("button", name="Add Grade").click()
        grade_names = page.locator(".grades-sub-row").locator(
            'input:not([type="number"])'
        )
        grade_names.nth(1).fill("Jumbo")
        # Close via toggle — values flush to the row.
        page.locator(".grades-toggle-btn").first.click()
        expect(page.locator(".grades-sub-row")).to_have_count(0)
        expect(page.locator(".grades-count").first).to_have_text("2")

    def test_column_copy_paste(self, admin_browser_context, live_server):
        page = admin_browser_context.new_page()
        _goto_bulk(page, live_server)
        page.locator("#add-row-btn").click()

        desc_cell = _row(page, 0).locator('td[data-col-type="description"]')
        desc_cell.locator("input").fill("copied text")
        desc_cell.hover()
        desc_cell.locator(".cell-copy-btn").click(force=True)

        target_cell = _row(page, 1).locator('td[data-col-type="description"]')
        page.wait_for_function(
            """() => document.querySelectorAll('.bulk-data-row')[1]
                .querySelector('td[data-col-type="description"]')
                .classList.contains('has-clipboard')"""
        )
        target_cell.hover()
        target_cell.locator(".cell-paste-btn").click(force=True)
        expect(target_cell.locator("input")).to_have_value("copied text")

    def test_draft_restores_on_reload(self, admin_browser_context, live_server):
        page = admin_browser_context.new_page()
        _goto_bulk(page, live_server)
        page.locator("#add-row-btn").click()
        _fill_name(page, 0, "DraftPinA")
        _fill_name(page, 1, "DraftPinB")
        page.wait_for_timeout(500)  # debounced draft save

        page.reload(wait_until="networkidle")
        rows = page.locator('.bulk-data-row input[data-field="name"]')
        expect(rows).to_have_count(2)
        expect(rows.nth(0)).to_have_value("DraftPinA")
        expect(rows.nth(1)).to_have_value("DraftPinB")

    def test_duplicate_name_warning(self, admin_browser_context, live_server, make_pin):
        make_pin("BulkDupName", tag_names=["bulkdup-tag"])
        page = admin_browser_context.new_page()
        _goto_bulk(page, live_server)
        _fill_name(page, 0, "BulkDupName")
        # Debounced check (1s) then fragment fetch.
        page.wait_for_function(
            """() => {
                const el = document.querySelector('.name-availability-feedback');
                return el && el.textContent.trim().length > 0;
            }""",
            timeout=10_000,
        )

    def test_grid_visual_baseline(
        self, admin_browser_context, live_server, assert_screenshot
    ):
        page = admin_browser_context.new_page()
        _goto_bulk(page, live_server)
        assert_screenshot(
            page.locator("div.overflow-x-auto").first,
            "bulk-import-grid-empty-row",
        )
