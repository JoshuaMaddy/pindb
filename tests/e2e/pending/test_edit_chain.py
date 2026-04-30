"""Multi-step pending-edit chain flows.

Covers behaviour that lives at the intersection of:
  * `routes/edit/shop.py` (POST creates a `PendingEdit` row when the editor
    is editing an approved canonical entity).
  * `routes/approve.py` (`approve-edits`, `reject-edits`, `delete-edits`
    against the chain).
  * `database/pending_edit_utils.py` (`get_edit_chain`, `get_head_edit`,
    `apply_snapshot_in_memory`, `get_effective_snapshot`).

These are the highest-leverage e2e checks: they exercise the chained-state
machine end-to-end through the real UI and DB, where most regressions hide.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from tests.e2e._pages import (
    PendingQueuePage,
    ShopDetailPage,
    ShopEditPage,
    ShopListPage,
)


def _shop_name_in_db(db_handle, shop_id: int) -> str:
    rows = db_handle("SELECT name FROM shops WHERE id = %s", (shop_id,))
    assert rows, f"shop {shop_id} missing"
    return rows[0][0]


def _pending_edits(db_handle, shop_id: int) -> list[tuple]:
    return db_handle(
        "SELECT id, parent_id, created_by_id, approved_at, rejected_at, patch "
        "FROM pending_edits "
        "WHERE entity_type = 'shops' AND entity_id = %s "
        "ORDER BY id ASC",
        (shop_id,),
    )


@pytest.mark.slow
class TestEditChainBuildup:
    def test_two_editors_stack_edits_into_a_chain(
        self,
        editor_browser_context,
        second_editor_browser_context,
        live_server,
        make_shop,
        db_handle,
    ):
        """Editor A edits → pending edit. Editor B opens, sees A's snapshot,
        submits another edit → second pending edit chained to the first.

        The canonical row must remain unchanged throughout.
        """
        shop = make_shop("ChainTarget", description="orig desc", approved=True)
        shop_id = int(shop["id"])

        # --- Editor A: rename ---
        page_a = editor_browser_context.new_page()
        ShopEditPage(page_a, live_server).goto(shop_id).submit(name="ChainTarget v2")

        # --- Editor B: open the edit page; the form should pre-populate with
        # the *effective* (post-A) snapshot, not the canonical name. ---
        page_b = second_editor_browser_context.new_page()
        edit_page_b = ShopEditPage(page_b, live_server).goto(shop_id)
        assert edit_page_b.name_value() == "ChainTarget v2"

        # Editor B then changes the description.
        edit_page_b.submit(description="edited by B")

        # Canonical untouched.
        assert _shop_name_in_db(db_handle, shop_id) == "ChainTarget"

        # Two pending edits, chained.
        edits = _pending_edits(db_handle, shop_id)
        assert len(edits) == 2
        first, second = edits
        assert second[1] == first[0], "second edit should reference first as parent"
        assert first[2] != second[2], "edits should be by different users"

    def test_admin_approve_edits_collapses_chain_in_order(
        self,
        editor_browser_context,
        second_editor_browser_context,
        admin_browser_context,
        live_server,
        make_shop,
        db_handle,
    ):
        shop = make_shop("MergeMe", description="d0", approved=True)
        shop_id = int(shop["id"])

        ShopEditPage(editor_browser_context.new_page(), live_server).goto(
            shop_id
        ).submit(name="MergeMe v2")
        ShopEditPage(second_editor_browser_context.new_page(), live_server).goto(
            shop_id
        ).submit(description="final desc")

        admin_page = admin_browser_context.new_page()
        PendingQueuePage(admin_page, live_server).goto().approve_edits(
            "shop", "MergeMe"
        )

        rows = db_handle(
            "SELECT name, description FROM shops WHERE id = %s", (shop_id,)
        )
        assert rows[0] == ("MergeMe v2", "final desc")

        # Both pending edits flipped to approved.
        edits = _pending_edits(db_handle, shop_id)
        assert len(edits) == 2
        assert all(row[3] is not None for row in edits), "all approved_at set"
        assert all(row[4] is None for row in edits), "no rejected_at set"


@pytest.mark.slow
class TestEditChainNegative:
    def test_reject_edits_keeps_chain_invisible_but_preserved(
        self,
        editor_browser_context,
        admin_browser_context,
        live_server,
        make_shop,
        db_handle,
    ):
        shop = make_shop("RejectKept", approved=True)
        shop_id = int(shop["id"])

        ShopEditPage(editor_browser_context.new_page(), live_server).goto(
            shop_id
        ).submit(name="RejectKept v2")

        admin_page = admin_browser_context.new_page()
        PendingQueuePage(admin_page, live_server).goto().reject_edits(
            "shop", "RejectKept"
        )

        # Chain still exists in DB but is marked rejected — get_edit_chain
        # filters rejected edits, so editor's edit page should fall back to
        # the canonical snapshot.
        rows = _pending_edits(db_handle, shop_id)
        assert len(rows) == 1
        assert rows[0][4] is not None, "rejected_at set"
        assert rows[0][3] is None, "approved_at not set"

        # Editor opens the edit page again and sees canonical name.
        editor_page = editor_browser_context.new_page()
        edit_page = ShopEditPage(editor_page, live_server).goto(shop_id)
        assert edit_page.name_value() == "RejectKept"

        # Submitting a fresh edit creates a new chain (separate from rejected).
        edit_page.submit(name="RejectKept v3")
        rows = _pending_edits(db_handle, shop_id)
        assert len(rows) == 2, "rejected edit retained, plus the new pending one"
        rejected_count = sum(1 for r in rows if r[4] is not None)
        pending_count = sum(1 for r in rows if r[3] is None and r[4] is None)
        assert rejected_count == 1
        assert pending_count == 1

    def test_delete_edits_wipes_chain_and_canonical_unchanged(
        self,
        editor_browser_context,
        admin_browser_context,
        live_server,
        make_shop,
        db_handle,
    ):
        shop = make_shop("WipeMe", approved=True)
        shop_id = int(shop["id"])

        ShopEditPage(editor_browser_context.new_page(), live_server).goto(
            shop_id
        ).submit(name="WipeMe v2")

        admin_page = admin_browser_context.new_page()
        PendingQueuePage(admin_page, live_server).goto().delete_edits("shop", "WipeMe")

        # Chain is hard-deleted; canonical untouched.
        assert _pending_edits(db_handle, shop_id) == []
        assert _shop_name_in_db(db_handle, shop_id) == "WipeMe"


@pytest.mark.slow
class TestPendingBannerLinksWork:
    def test_view_pending_link_navigates_to_pending_view(
        self,
        editor_browser_context,
        admin_browser_context,
        live_server,
        make_shop,
    ):
        shop = make_shop("BannerLink", approved=True)
        shop_id = int(shop["id"])

        ShopEditPage(editor_browser_context.new_page(), live_server).goto(
            shop_id
        ).submit(name="BannerLink v2")

        admin_page = admin_browser_context.new_page()
        ShopDetailPage(admin_page, live_server).goto(shop_id)
        # Banner present, with a "View pending →" link.
        link = admin_page.locator("a", has_text="View pending")
        link.first.click()
        admin_page.wait_for_load_state("load")

        # On the pending view we should now see the editor's proposed name.
        # (The pending view uses ?version=pending and renders the snapshot.)
        expect(admin_page.locator("body")).to_contain_text("BannerLink v2")

    def test_anonymous_visiting_canonical_does_not_see_proposed_name(
        self,
        editor_browser_context,
        anon_browser_context,
        live_server,
        make_shop,
    ):
        shop = make_shop("AnonShop", approved=True)
        shop_id = int(shop["id"])

        ShopEditPage(editor_browser_context.new_page(), live_server).goto(
            shop_id
        ).submit(name="AnonShop v2")

        anon_page = anon_browser_context.new_page()
        ShopListPage(anon_page, live_server).goto()
        expect(anon_page.locator("body")).to_contain_text("AnonShop")
        expect(anon_page.locator("body")).not_to_contain_text("AnonShop v2")
