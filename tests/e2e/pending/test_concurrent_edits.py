"""Concurrent and stale-state flows — multiple browser contexts hitting
the same entity in interleaved orders.

These are the scenarios most likely to expose race conditions or stale
read-modify-write bugs. We don't need *true* parallelism (which Playwright
sync API can't do anyway) — we just need interleaved actions across two
authenticated browser contexts and assertions on the resulting DB state.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from tests.e2e._pages import (
    PendingQueuePage,
    ShopDetailPage,
    ShopEditPage,
)


def _shop_row(db_handle, shop_id: int) -> tuple:
    rows = db_handle("SELECT name, description FROM shops WHERE id = %s", (shop_id,))
    assert rows
    return rows[0]


def _pending_edit_count(db_handle, shop_id: int) -> int:
    rows = db_handle(
        "SELECT COUNT(*) FROM pending_edits "
        "WHERE entity_type = 'shops' AND entity_id = %s "
        "AND approved_at IS NULL AND rejected_at IS NULL",
        (shop_id,),
    )
    return int(rows[0][0])


@pytest.mark.slow
class TestInterleavedEdits:
    def test_two_editors_submit_independent_edits_both_landed(
        self,
        editor_browser_context,
        second_editor_browser_context,
        live_server,
        make_shop,
        db_handle,
    ):
        """Editor A and Editor B both open the edit page on a fresh
        approved shop, then submit different changes. Both pending edits
        should land on the chain (no clobbering)."""
        shop = make_shop("RaceShop", description="d0", approved=True)
        shop_id = int(shop["id"])

        # Both editors load the edit form before either submits.
        page_a = editor_browser_context.new_page()
        page_b = second_editor_browser_context.new_page()
        edit_a = ShopEditPage(page_a, live_server).goto(shop_id)
        edit_b = ShopEditPage(page_b, live_server).goto(shop_id)

        # Both saw the canonical name at load time.
        assert edit_a.name_value() == "RaceShop"
        assert edit_b.name_value() == "RaceShop"

        # Editor A submits first.
        edit_a.submit(name="RaceShop A")
        # Editor B submits next; their snapshot is now stale (they
        # still see "RaceShop"), but the system should still chain
        # their edit on top of A's.
        edit_b.submit(description="d-by-b")

        # Both edits accepted, canonical untouched.
        assert _pending_edit_count(db_handle, shop_id) == 2
        assert _shop_row(db_handle, shop_id) == ("RaceShop", "d0")

    def test_admin_edit_during_pending_overwrites_canonical_only(
        self,
        editor_browser_context,
        admin_browser_context,
        live_server,
        make_shop,
        db_handle,
    ):
        """Admin can directly edit a canonical row while a pending edit
        is in flight. The pending edit chain remains intact and is
        still applicable."""
        shop = make_shop("AdminBypass", description="d0", approved=True)
        shop_id = int(shop["id"])

        # Editor submits an edit (becomes pending).
        ShopEditPage(editor_browser_context.new_page(), live_server).goto(
            shop_id
        ).submit(name="AdminBypass v2")

        # Admin then edits the canonical row directly (admin edits skip
        # the pending flow per `needs_pending_edit`).
        ShopEditPage(admin_browser_context.new_page(), live_server).goto(
            shop_id
        ).submit(description="d-from-admin")

        name, desc = _shop_row(db_handle, shop_id)
        assert name == "AdminBypass", "admin edit must not affect name"
        assert desc == "d-from-admin", "admin edit applied to description"

        # Editor's pending edit still in the queue.
        assert _pending_edit_count(db_handle, shop_id) == 1

    def test_admin_approves_after_admin_canonical_edit(
        self,
        editor_browser_context,
        admin_browser_context,
        live_server,
        make_shop,
        db_handle,
    ):
        """If the admin both edits canonical AND later approves the
        editor's pending edit, the editor's patch lands on top of the
        admin's intermediate state."""
        shop = make_shop("Stack", description="d0", approved=True)
        shop_id = int(shop["id"])

        # Editor proposes a name change.
        ShopEditPage(editor_browser_context.new_page(), live_server).goto(
            shop_id
        ).submit(name="Stack v2")

        # Admin tweaks description directly.
        ShopEditPage(admin_browser_context.new_page(), live_server).goto(
            shop_id
        ).submit(description="d-admin")

        # Admin then approves the editor's chain.
        admin_page = admin_browser_context.new_page()
        PendingQueuePage(admin_page, live_server).goto().approve_edits("shop", "Stack")

        name, desc = _shop_row(db_handle, shop_id)
        # Name moved to the editor's proposed value.
        assert name == "Stack v2"
        # Admin's description change must NOT be reverted by the patch
        # (the editor never touched description in their edit, so the
        # snapshot patch should not contain it).
        assert desc == "d-admin", (
            f"approve-edits clobbered an unrelated admin change (got desc={desc!r})"
        )


@pytest.mark.slow
class TestPendingBannerDisappearsAfterApprove:
    def test_banner_gone_once_admin_approves_chain(
        self,
        editor_browser_context,
        admin_browser_context,
        live_server,
        make_shop,
    ):
        shop = make_shop("BannerGone", approved=True)
        shop_id = int(shop["id"])

        ShopEditPage(editor_browser_context.new_page(), live_server).goto(
            shop_id
        ).submit(name="BannerGone v2")

        admin_page = admin_browser_context.new_page()
        # Banner present pre-approval.
        ShopDetailPage(admin_page, live_server).goto(shop_id)
        expect(
            admin_page.get_by_text("This entry has a pending edit awaiting approval.")
        ).to_be_visible()

        # Approve the chain.
        PendingQueuePage(admin_page, live_server).goto().approve_edits(
            "shop", "BannerGone"
        )

        # Reload the canonical view; banner should be gone.
        ShopDetailPage(admin_page, live_server).goto(shop_id)
        expect(
            admin_page.get_by_text("This entry has a pending edit awaiting approval.")
        ).to_have_count(0)
        # Canonical now reflects the editor's name.
        expect(admin_page.locator("body")).to_contain_text("BannerGone v2")
