"""Cross-role visibility matrix at the browser level.

Verifies the rules in `audit_events._filter_deleted` end-to-end — i.e. who
can actually *see* a given entity in a given lifecycle state.

The matrix:

| viewer | approved | pending | rejected |
|--------|----------|---------|----------|
| anon   | visible  | hidden  | hidden   |
| user   | visible  | hidden  | hidden   |
| editor | visible  | visible | hidden   |
| admin  | visible  | visible | visible  |

Soft-delete state is exercised in ``pending/test_edit_chain.py`` (delete-edits +
delete-pending paths) and the integration suite; we focus here on the
pending/rejected axis where editor and admin diverge from regular users.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext


def _shop_visible_in_list(context: BrowserContext, base_url: str, name: str) -> bool:
    page = context.new_page()
    try:
        page.goto(f"{base_url}/list/shops")
        page.wait_for_load_state("load")
        return page.get_by_text(name).count() > 0
    finally:
        page.close()


def _shop_detail_reachable(
    context: BrowserContext, base_url: str, shop_id: int
) -> bool:
    """Whether the shop detail page renders for this viewer.

    A hidden entity redirects to ``/`` (the route returns ``RedirectResponse``
    rather than a 404). When the page is reachable, the bare-id URL is
    rewritten by `canonical_slug_redirect` to ``/get/shop/{slug}/{id}``, so we
    accept either form.
    """
    page = context.new_page()
    try:
        page.goto(f"{base_url}/get/shop/{shop_id}")
        return bool(re.search(rf"/get/shop/(?:[^/]+/)?{shop_id}/?$", page.url))
    finally:
        page.close()


def _reject_via_admin(db_handle, shop_id: int, admin_user_id_row) -> None:
    """Mark a shop rejected directly in the DB (faster than the UI)."""
    admin_id = admin_user_id_row[0][0]
    db_handle(
        "UPDATE shops SET rejected_at = NOW(), rejected_by_id = %s WHERE id = %s",
        (admin_id, shop_id),
    )


@pytest.fixture
def admin_user_id(db_handle):
    return db_handle("SELECT id FROM users WHERE username = 'e2e_admin_pw'")


# ---------------------------------------------------------------------------
# APPROVED entities
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestApprovedVisibility:
    def test_approved_shop_visible_to_everyone(
        self,
        anon_browser_context,
        regular_user_browser_context,
        editor_browser_context,
        admin_browser_context,
        live_server,
        make_shop,
    ):
        make_shop("PublicShop", approved=True)

        for ctx in (
            anon_browser_context,
            regular_user_browser_context,
            editor_browser_context,
            admin_browser_context,
        ):
            assert _shop_visible_in_list(ctx, live_server, "PublicShop"), (
                f"approved shop hidden from {ctx}"
            )


# ---------------------------------------------------------------------------
# PENDING entities
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestPendingVisibility:
    def test_pending_shop_visible_only_to_editor_and_admin(
        self,
        anon_browser_context,
        regular_user_browser_context,
        editor_browser_context,
        admin_browser_context,
        live_server,
        make_shop,
    ):
        make_shop("PendingShop", approved=False)

        # Hidden from anon + regular user.
        assert not _shop_visible_in_list(
            anon_browser_context, live_server, "PendingShop"
        )
        assert not _shop_visible_in_list(
            regular_user_browser_context, live_server, "PendingShop"
        )

        # Visible to editor + admin (they can see the pending row in
        # the list page so they can approve/edit it).
        assert _shop_visible_in_list(editor_browser_context, live_server, "PendingShop")
        assert _shop_visible_in_list(admin_browser_context, live_server, "PendingShop")

    def test_pending_shop_detail_404s_for_anon_but_loads_for_editor(
        self,
        anon_browser_context,
        editor_browser_context,
        live_server,
        make_shop,
        db_handle,
    ):
        make_shop("DetailPending", approved=False)
        rows = db_handle("SELECT id FROM shops WHERE name = 'DetailPending'")
        shop_id = rows[0][0]

        # Anonymous: filtered out → redirect to "/". Editor: 200 detail page.
        assert not _shop_detail_reachable(anon_browser_context, live_server, shop_id)
        assert _shop_detail_reachable(editor_browser_context, live_server, shop_id)


# ---------------------------------------------------------------------------
# REJECTED entities
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestRejectedVisibility:
    def test_rejected_shop_hidden_from_everyone_in_default_views(
        self,
        anon_browser_context,
        regular_user_browser_context,
        editor_browser_context,
        admin_browser_context,
        live_server,
        make_shop,
        db_handle,
        admin_user_id,
    ):
        make_shop("RejectedShop", approved=False)
        rows = db_handle("SELECT id FROM shops WHERE name = 'RejectedShop'")
        shop_id = rows[0][0]
        _reject_via_admin(db_handle, shop_id, admin_user_id)

        # Filtered from default list view for anon, user, editor, AND admin
        # (admin needs include_pending=True to see rejected items, which
        # only the approval queue uses).
        for ctx in (
            anon_browser_context,
            regular_user_browser_context,
            editor_browser_context,
            admin_browser_context,
        ):
            assert not _shop_visible_in_list(ctx, live_server, "RejectedShop"), (
                f"rejected shop leaked into list view for {ctx}"
            )
