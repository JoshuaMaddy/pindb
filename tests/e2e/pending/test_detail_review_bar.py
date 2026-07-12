"""The admin review bar on a pending entry's own detail page.

The queue only lists an entry; an admin who opens it to actually look at the
submission gets the same three actions there, and is walked back to the page they
came from once they rule on it.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Locator, Page, expect

from tests.e2e._pages import PendingQueuePage

REASON = "The description is empty — please say what this shop sells and where it ships from."


def _open_from_queue(page: Page, live_server: str, name: str) -> None:
    """Click through from the queue so the detail page has real history to go back to."""
    PendingQueuePage(page, live_server).goto()
    page.get_by_role("link", name=name).first.click()
    page.wait_for_url(re.compile(r"/get/shop/"))


def _act(page: Page, action: str) -> None:
    """Click a review-bar action and wait for the POST and the walk back."""
    form = page.locator(f"form[action*='/admin/pending/{action}/shop/']")
    with page.expect_response(
        lambda response: (
            response.request.method == "POST" and "/admin/pending/" in response.url
        )
    ):
        form.locator("button[type='submit']").click()
    page.wait_for_url(re.compile(r"/admin/pending$"))


def _open_change_request(page: Page) -> Locator:
    page.get_by_role("button", name="Request changes").first.click()
    form = page.locator("form[action*='/admin/pending/reject/shop/']")
    form.wait_for(state="visible")
    return form


@pytest.mark.slow
class TestDetailReviewBar:
    def test_approve_from_the_detail_page_returns_to_the_queue(
        self, admin_browser_context, live_server, make_shop, db_handle
    ):
        shop_id = int(make_shop("BarApproveShop", approved=False)["id"])

        page = admin_browser_context.new_page()
        _open_from_queue(page, live_server, "BarApproveShop")
        expect(page.get_by_text("Awaiting review.")).to_be_visible()

        _act(page, "approve")

        rows = db_handle("SELECT approved_at FROM shops WHERE id = %s", (shop_id,))
        assert rows[0][0] is not None, "the bar's Approve approves the entry"
        # Back on the queue, refreshed rather than restored stale from the bfcache.
        expect(page.get_by_role("link", name="BarApproveShop")).to_have_count(0)

    def test_request_changes_from_the_detail_page(
        self, admin_browser_context, live_server, make_shop, db_handle
    ):
        shop_id = int(make_shop("BarRejectShop", approved=False)["id"])

        page = admin_browser_context.new_page()
        _open_from_queue(page, live_server, "BarRejectShop")

        form = _open_change_request(page)
        form.locator("textarea[name='reason']").fill(REASON)
        with page.expect_response(
            lambda response: (
                response.request.method == "POST" and "/admin/pending/" in response.url
            )
        ):
            form.get_by_role("button", name="Request changes").click()
        page.wait_for_url(re.compile(r"/admin/pending$"))

        rows = db_handle(
            "SELECT rejected_at, rejection_reason FROM shops WHERE id = %s", (shop_id,)
        )
        assert rows[0][0] is not None
        assert rows[0][1] == REASON
        expect(page.get_by_role("heading", name="Needs Changes")).to_be_visible()

    def test_delete_from_the_detail_page(
        self, admin_browser_context, live_server, make_shop, db_handle
    ):
        shop_id = int(make_shop("BarDeleteShop", approved=False)["id"])

        page = admin_browser_context.new_page()
        _open_from_queue(page, live_server, "BarDeleteShop")
        page.get_by_role("button", name="Delete", exact=True).click()

        _act(page, "delete")

        rows = db_handle("SELECT deleted_at FROM shops WHERE id = %s", (shop_id,))
        assert rows[0][0] is not None, "the bar's Delete soft-deletes the entry"

    def test_a_needs_changes_entry_offers_approve_and_delete_only(
        self, admin_browser_context, live_server, make_shop
    ):
        """Asking for changes a second time says nothing new — same as the queue."""
        make_shop("BarSentBackShop", approved=False)

        page = admin_browser_context.new_page()
        queue = PendingQueuePage(page, live_server).goto()
        queue.request_changes("shop", "BarSentBackShop", REASON)

        page.get_by_role("link", name="BarSentBackShop").first.click()
        page.wait_for_url(re.compile(r"/get/shop/"))

        expect(
            page.get_by_text("Sent back for changes — waiting on the submitter.")
        ).to_be_visible()
        expect(page.get_by_role("button", name="Approve")).to_be_visible()
        expect(page.get_by_role("button", name="Delete", exact=True)).to_be_visible()
        expect(page.get_by_role("button", name="Request changes")).to_have_count(0)
        # The heading's Delete (which posts to /delete/{type}/{id} and cannot see an
        # unapproved row) steps aside for the bar's, so there is only one Delete.
        expect(page.get_by_role("button", name="Delete shop")).to_have_count(0)

    def test_the_bar_is_admin_only(
        self, editor_browser_context, live_server, make_shop
    ):
        """An editor sees their own pending entry, but cannot rule on it."""
        shop_id = int(make_shop("BarEditorShop", approved=False)["id"])

        page = editor_browser_context.new_page()
        page.goto(f"{live_server}/get/shop/{shop_id}", wait_until="networkidle")

        expect(
            page.get_by_role("heading", name=re.compile("BarEditorShop"))
        ).to_be_visible()
        expect(page.get_by_text("Awaiting review.")).to_have_count(0)
        expect(page.get_by_role("button", name="Approve")).to_have_count(0)
