"""The admin review bar for a pending *edit chain* on the entity's own page.

Sibling of `test_detail_review_bar.py`, which covers the bar for an unapproved
*entry*. This one covers the bar for a pending edit to an already-approved
entry: different routes (`/admin/pending/*-edits/`), a Delete that discards the
submission rather than the entry, and `?after=reload` instead of `?after=back` —
ruling on an edit leaves the page standing, so the admin stays put and htmx
re-renders in place.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Locator, Page, expect

from tests.e2e._pages import ShopDetailPage, ShopEditPage

REASON = "The description is empty — please say what this shop sells and where it ships from."


def _propose_edit(editor_browser_context, live_server, shop_id: int, name: str) -> None:
    """An editor renames the approved shop, which lands as a pending edit."""
    page = editor_browser_context.new_page()
    ShopEditPage(page, live_server).goto(shop_id).submit(name=name)
    page.close()


def _open_as_admin(admin_browser_context, live_server, shop_id: int) -> Page:
    page = admin_browser_context.new_page()
    ShopDetailPage(page, live_server).goto(shop_id)
    return page


def _act(page: Page, action: str) -> None:
    """Click a bar action and wait for the POST plus htmx's HX-Refresh reload.

    The bar answers 204 + ``HX-Refresh: true``, so htmx reloads the page in
    place — the URL is unchanged, which is the whole point of ``after=reload``.
    Waiting on the ``load`` event is what distinguishes that from no reload at
    all; a URL predicate would match the page already open.
    """
    form = page.locator(f"form[action*='/admin/pending/{action}-edits/shop/']")
    with page.expect_event("load"):
        with page.expect_response(
            lambda response: (
                response.request.method == "POST"
                and f"/{action}-edits/shop/" in response.url
            )
        ):
            form.locator("button[type='submit']").click()


def _open_change_request(page: Page) -> Locator:
    page.get_by_role("button", name="Request changes").first.click()
    form = page.locator("form[action*='/admin/pending/reject-edits/shop/']")
    form.wait_for(state="visible")
    return form


def _pending_edits(db_handle, shop_id: int) -> list[tuple]:
    return db_handle(
        "SELECT approved_at, rejected_at, rejection_reason FROM pending_edits "
        "WHERE entity_type = 'shops' AND entity_id = %s ORDER BY id ASC",
        (shop_id,),
    )


def _shop_name(db_handle, shop_id: int) -> str:
    return db_handle("SELECT name FROM shops WHERE id = %s", (shop_id,))[0][0]


@pytest.mark.slow
class TestDetailEditReviewBar:
    def test_approve_the_edit_from_the_detail_page(
        self,
        admin_browser_context,
        editor_browser_context,
        live_server,
        make_shop,
        db_handle,
    ):
        shop_id = int(make_shop("EditBarApprove", approved=True)["id"])
        _propose_edit(
            editor_browser_context, live_server, shop_id, "EditBarApprove Renamed"
        )

        page = _open_as_admin(admin_browser_context, live_server, shop_id)
        expect(page.get_by_text("Pending edit awaiting review.")).to_be_visible()

        _act(page, "approve")

        assert _shop_name(db_handle, shop_id) == "EditBarApprove Renamed"
        assert _pending_edits(db_handle, shop_id)[0][0] is not None
        # The page stayed put and re-rendered without its pending banner.
        expect(page.get_by_text("Pending edit awaiting review.")).to_have_count(0)
        expect(
            page.get_by_role("heading", name=re.compile("EditBarApprove Renamed"))
        ).to_be_visible()

    def test_request_changes_on_the_edit_from_the_detail_page(
        self,
        admin_browser_context,
        editor_browser_context,
        live_server,
        make_shop,
        db_handle,
    ):
        shop_id = int(make_shop("EditBarReject", approved=True)["id"])
        _propose_edit(
            editor_browser_context, live_server, shop_id, "EditBarReject Renamed"
        )

        page = _open_as_admin(admin_browser_context, live_server, shop_id)
        form = _open_change_request(page)
        form.locator("textarea[name='reason']").fill(REASON)
        with page.expect_event("load"):
            with page.expect_response(
                lambda response: (
                    response.request.method == "POST"
                    and "/reject-edits/shop/" in response.url
                )
            ):
                form.get_by_role("button", name="Request changes").click()

        _, rejected_at, reason = _pending_edits(db_handle, shop_id)[0]
        assert rejected_at is not None
        assert reason == REASON
        # The canonical row is untouched by an edit rejection.
        assert _shop_name(db_handle, shop_id) == "EditBarReject"
        expect(
            page.get_by_text("Edit sent back for changes — waiting on the submitter.")
        ).to_be_visible()

    def test_discard_the_edit_leaves_the_entry_alone(
        self,
        admin_browser_context,
        editor_browser_context,
        live_server,
        make_shop,
        db_handle,
    ):
        shop_id = int(make_shop("EditBarDiscard", approved=True)["id"])
        _propose_edit(
            editor_browser_context, live_server, shop_id, "EditBarDiscard Renamed"
        )

        page = _open_as_admin(admin_browser_context, live_server, shop_id)
        page.get_by_role("button", name="Discard edit").click()

        _act(page, "delete")

        assert _pending_edits(db_handle, shop_id) == []
        assert _shop_name(db_handle, shop_id) == "EditBarDiscard"
        assert (
            db_handle("SELECT deleted_at FROM shops WHERE id = %s", (shop_id,))[0][0]
            is None
        ), "discarding the edit must not delete the entry"

    def test_a_sent_back_edit_offers_approve_and_discard_only(
        self,
        admin_browser_context,
        editor_browser_context,
        live_server,
        make_shop,
    ):
        shop_id = int(make_shop("EditBarSentBack", approved=True)["id"])
        _propose_edit(
            editor_browser_context, live_server, shop_id, "EditBarSentBack Renamed"
        )

        page = _open_as_admin(admin_browser_context, live_server, shop_id)
        form = _open_change_request(page)
        form.locator("textarea[name='reason']").fill(REASON)
        with page.expect_event("load"):
            form.get_by_role("button", name="Request changes").click()

        expect(page.get_by_role("button", name="Approve edit")).to_be_visible()
        expect(page.get_by_role("button", name="Discard edit")).to_be_visible()
        expect(page.get_by_role("button", name="Request changes")).to_have_count(0)

    def test_the_edit_bar_is_admin_only(
        self, editor_browser_context, live_server, make_shop
    ):
        """The editor who submitted the edit sees it pending, but cannot rule on it."""
        shop_id = int(make_shop("EditBarEditorOnly", approved=True)["id"])
        _propose_edit(
            editor_browser_context, live_server, shop_id, "EditBarEditorOnly Renamed"
        )

        page = editor_browser_context.new_page()
        detail = ShopDetailPage(page, live_server).goto(shop_id)

        expect(detail.pending_edit_banner()).to_be_visible()
        expect(page.get_by_text("Pending edit awaiting review.")).to_have_count(0)
        expect(page.get_by_role("button", name="Approve edit")).to_have_count(0)
