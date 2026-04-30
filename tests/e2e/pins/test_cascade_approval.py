"""Cascade approval when admin approves a pending pin."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from playwright.sync_api import expect

from tests.e2e.pins._helpers import create_pin_via_http, editor_login_http


@pytest.mark.slow
class TestPinCascadeApproval:
    def test_approving_pin_cascades_pending_shop_and_artist(
        self,
        admin_browser_context,
        live_server,
        db_handle,
        make_shop,
        make_artist,
    ):
        shop = make_shop("CascadeShop", approved=False)
        artist = make_artist("CascadeArtist", approved=False)

        client = editor_login_http(live_server)
        try:
            response = create_pin_via_http(
                client,
                name="CascadePin",
                shop_ids=[int(shop["id"])],
                artist_ids=[int(artist["id"])],
            )
            assert response.status_code == 200, response.text[:500]
        finally:
            client.close()

        pin_rows = db_handle(
            "SELECT id, approved_at FROM pins WHERE name = 'CascadePin'"
        )
        assert pin_rows and pin_rows[0][1] is None

        admin_page = admin_browser_context.new_page()
        admin_page.goto(f"{live_server}/admin/pending")
        admin_page.wait_for_load_state("load")
        pin_row = admin_page.locator("tr", has_text="CascadePin")
        expect(pin_row).to_contain_text("Will also approve")
        pin_row.locator("form[action*='/admin/pending/approve/pin/']").locator(
            "button[type='submit']"
        ).click()
        admin_page.wait_for_load_state("load")

        pin_rows = db_handle("SELECT approved_at FROM pins WHERE name = 'CascadePin'")
        shop_rows = db_handle(
            "SELECT approved_at FROM shops WHERE name = 'CascadeShop'"
        )
        artist_rows = db_handle(
            "SELECT approved_at FROM artists WHERE name = 'CascadeArtist'"
        )
        assert pin_rows[0][0] is not None, "pin not approved"
        assert shop_rows[0][0] is not None, "shop not cascaded"
        assert artist_rows[0][0] is not None, "artist not cascaded"


@pytest.mark.slow
class TestPendingQueueCascadeHint:
    def test_will_also_approve_lists_pending_dependencies(
        self,
        admin_browser_context,
        live_server,
        make_shop: Callable[..., dict[str, Any]],
    ):
        pending_shop = make_shop("HintShop", approved=False)

        client = editor_login_http(live_server)
        try:
            response = create_pin_via_http(
                client,
                name="HintPin",
                shop_ids=[int(pending_shop["id"])],
            )
            assert response.status_code == 200, response.text[:500]
        finally:
            client.close()

        admin_page = admin_browser_context.new_page()
        admin_page.goto(f"{live_server}/admin/pending")
        admin_page.wait_for_load_state("load")
        pin_row = admin_page.locator("tr", has_text="HintPin")
        expect(pin_row).to_contain_text("Will also approve: HintShop")
