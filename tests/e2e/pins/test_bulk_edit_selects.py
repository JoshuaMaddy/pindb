"""Bulk edit page select widgets: behavior contract for the native port.

Written against the legacy Tom Select controls (``pins/pin_creation.js``
initializes them on this page too) per the lockstep protocol; must pass
unchanged after the native MultiSelect port. The load-bearing interop: the
``tag_ids`` select carries ``hx-get``/``hx-trigger="load, change"`` for the
implication preview, so selecting a tag through the widget must fire a real
``change`` event the HTMX binding sees. Scalar enum selects and the apply
round-trip are covered too.
"""

from __future__ import annotations

import re

from playwright.sync_api import expect

from tests.e2e.select_helpers import multi_add, single_pick


class TestBulkEditSelects:
    def test_tag_pick_fires_preview_and_apply_roundtrips(
        self, admin_browser_context, live_server, make_pin, make_tag, db_handle
    ):
        base = make_tag("bulkedit_base", approved=True)
        extra = make_tag("bulkedit_extra", approved=True)
        pin = make_pin("BulkEditTarget", tag_names=["bulkedit_base"])

        page = admin_browser_context.new_page()
        page.goto(
            f"{live_server}/bulk-edit/from/tag/{base['id']}",
            wait_until="networkidle",
        )
        expect(page.get_by_text("This change will affect 1 pin(s).")).to_be_visible()

        # Selecting a tag must fire a change event the HTMX preview trigger
        # listens for (hx-trigger="load, change" on the select).
        with page.expect_request(
            lambda request: "implication" in request.url and "tag_ids" in request.url
        ):
            multi_add(
                page,
                page.locator("#tag_ids"),
                "bulkedit",
                option_text=re.compile(r"^\s*Bulkedit Extra\s*$", re.I),
            )

        # Scalar single-select + its apply checkbox.
        single_pick(
            page,
            page.locator("select[name='limited_edition_value']"),
            "Yes",
        )
        page.locator("#apply_limited_edition").check()

        with page.expect_response(
            lambda response: (
                response.request.method == "POST" and "/bulk-edit/apply" in response.url
            )
        ) as response_info:
            page.locator("input[type='submit']").click()
        assert response_info.value.status < 400

        tag_rows = db_handle(
            """SELECT tags.name FROM pins_tags
               JOIN tags ON tags.id = pins_tags.tag_id
               WHERE pins_tags.pin_id = %s ORDER BY tags.name""",
            (pin["id"],),
        )
        names = {name for (name,) in tag_rows}
        assert {"bulkedit_base", "bulkedit_extra"} <= names, tag_rows
        assert extra["id"] in {
            row[0]
            for row in db_handle(
                "SELECT tag_id FROM pins_tags WHERE pin_id = %s", (pin["id"],)
            )
        }
        limited = db_handle(
            "SELECT limited_edition FROM pins WHERE id = %s", (pin["id"],)
        )
        assert limited == [(True,)]
