"""The needs-changes loop, end to end through the real UI.

An admin sends a submission back with a reason; the editor is notified, sees the
reason on the entry, fixes it, and the entry returns to the pending queue.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from tests.e2e._pages import PendingQueuePage, ShopEditPage, submit_pending_action

REASON = "The description is empty — please say what this shop sells and where it ships from."


@pytest.mark.slow
class TestChangeRequestGate:
    def test_submit_stays_disabled_until_the_reason_is_long_enough(
        self, admin_browser_context, live_server, make_shop
    ):
        """The reviewer has to say something actionable before they can send it back."""
        make_shop("GateShop", approved=False)

        page = admin_browser_context.new_page()
        queue = PendingQueuePage(page, live_server).goto()
        form = queue.open_change_request("GateShop")

        submit = form.get_by_role("button", name="Request changes")
        expect(submit).to_be_visible()
        expect(submit).to_be_disabled()

        reason_box = form.locator("textarea[name='reason']")
        reason_box.fill("too short")
        expect(submit).to_be_disabled()

        reason_box.fill(REASON)
        expect(submit).to_be_enabled()

        # Back under the minimum: the gate closes again.
        reason_box.fill("nope")
        expect(submit).to_be_disabled()
        page.keyboard.press("Escape")


@pytest.mark.slow
class TestNeedsChangesLoop:
    def test_change_request_reaches_the_editor_who_fixes_and_resubmits(
        self,
        admin_browser_context,
        editor_browser_context,
        live_server,
        make_shop,
        db_handle,
    ):
        shop = make_shop("LoopShop", approved=False)
        shop_id = int(shop["id"])

        # --- Admin sends it back with a reason ---
        admin_page = admin_browser_context.new_page()
        queue = PendingQueuePage(admin_page, live_server).goto()
        form = queue.open_change_request("LoopShop")
        form.locator("textarea[name='reason']").fill(REASON)
        submit_pending_action(admin_page, form)

        # It leaves the admin's queue and lands in Needs Changes, reason and all.
        expect(admin_page.get_by_role("heading", name="Needs Changes")).to_be_visible()
        expect(admin_page.get_by_text(REASON).first).to_be_visible()

        rows = db_handle(
            "SELECT rejected_at, rejection_reason FROM shops WHERE id = %s", (shop_id,)
        )
        assert rows[0][0] is not None
        assert rows[0][1] == REASON

        # --- The editor is notified ---
        # Scope to the inbox list: the navbar hover-preview renders the same message
        # but stays hidden until hovered, so an unscoped locator matches it and fails.
        editor_page = editor_browser_context.new_page()
        editor_page.goto(f"{live_server}/messages", wait_until="networkidle")
        inbox = editor_page.locator("#messages-list")
        expect(
            inbox.get_by_text("Changes requested on your shop submission", exact=False)
        ).to_be_visible()
        expect(inbox.get_by_text(REASON)).to_be_visible()

        # --- And sees the reason on the entry itself ---
        editor_page.goto(f"{live_server}/get/shop/{shop_id}", wait_until="networkidle")
        expect(editor_page.get_by_text(REASON).first).to_be_visible()

        # --- The editor fixes it, which returns it to pending ---
        ShopEditPage(editor_page, live_server).goto(shop_id).submit(
            description="Enamel pins, shipped from Bristol."
        )

        rows = db_handle(
            "SELECT rejected_at, rejection_reason, approved_at FROM shops WHERE id = %s",
            (shop_id,),
        )
        assert rows[0][0] is None, "editing clears the needs-changes flag"
        assert rows[0][1] is None, "the stale reason is cleared with it"
        assert rows[0][2] is None, "resubmitting does not approve it"

        # Back in the admin's pending queue for a fresh decision.
        queue = PendingQueuePage(admin_browser_context.new_page(), live_server).goto()
        expect(
            queue.row_for_entity("LoopShop").get_by_role("button", name="Approve")
        ).to_be_visible()
