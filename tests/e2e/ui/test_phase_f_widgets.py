"""Phase F widget contracts: admin users table, confirm modal, delete-account
gate, navbar mobile menu, owned-panel tradeable flow.

Written against the legacy Alpine implementations first (lockstep protocol);
must pass unchanged after the island/vanilla ports.
"""

from __future__ import annotations

from playwright.sync_api import expect


class TestAdminUsersTable:
    def test_search_sort_paginate(
        self,
        admin_browser_context,
        editor_http_client,
        regular_user_browser_context,
        live_server,
    ):
        page = admin_browser_context.new_page()
        page.goto(f"{live_server}/admin/users", wait_until="networkidle")

        rows = page.locator("tbody tr")
        initial = rows.count()
        assert initial >= 3  # session users at minimum

        search = page.locator('input[type="search"]')
        search.fill("e2e_regular")
        expect(rows).to_have_count(1)
        expect(rows.first).to_contain_text("e2e_regular")

        search.fill("zz_no_such_user_zz")
        expect(rows).to_have_count(0)
        search.fill("")
        expect(rows).to_have_count(initial)

        # Sort by username toggles direction (arrow indicator changes).
        header = page.locator("th", has_text="Username").first
        header.click()
        first_after_sort = rows.first.inner_text()
        header.click()
        assert rows.first.inner_text() != first_after_sort

    def test_editor_promote_demote_roundtrip(
        self,
        admin_browser_context,
        regular_user_browser_context,
        live_server,
        db_handle,
    ):
        page = admin_browser_context.new_page()
        page.goto(f"{live_server}/admin/users", wait_until="networkidle")
        page.locator('input[type="search"]').fill("e2e_regular")
        row = page.locator("tbody tr").first
        expect(row).to_contain_text("e2e_regular")

        with page.expect_navigation():
            row.get_by_role("button", name="Promote to Editor").click()
        assert db_handle(
            "SELECT is_editor FROM users WHERE username = 'e2e_regular'"
        ) == [(True,)]

        page.locator('input[type="search"]').fill("e2e_regular")
        row = page.locator("tbody tr").first
        with page.expect_navigation():
            row.get_by_role("button", name="Revoke Editor").click()
        assert db_handle(
            "SELECT is_editor FROM users WHERE username = 'e2e_regular'"
        ) == [(False,)]


class TestConfirmModal:
    def test_cancel_then_confirm_deletes_tag(
        self, admin_browser_context, live_server, make_tag, db_handle
    ):
        tag = make_tag("confirm-modal-victim")
        page = admin_browser_context.new_page()
        page.goto(f"{live_server}/get/tag/{tag['id']}", wait_until="networkidle")

        trigger = page.get_by_title("Delete tag")
        trigger.click()
        modal_message = page.get_by_text('Delete the tag "confirm-modal-victim"?')
        expect(modal_message).to_be_visible()

        page.get_by_role("button", name="Cancel").click()
        expect(modal_message).not_to_be_visible()

        trigger.click()
        expect(modal_message).to_be_visible()
        with page.expect_response(
            lambda r: r.request.method == "POST" and "/delete/tag/" in r.url
        ) as response_info:
            page.get_by_role("button", name="Delete", exact=True).click()
        assert response_info.value.status < 400

        rows = db_handle(
            "SELECT deleted_at IS NOT NULL FROM tags WHERE id = %s",
            (tag["id"],),
        )
        assert rows == [(True,)]


class TestDeleteAccountGate:
    def test_typing_username_enables_submit(
        self, regular_user_browser_context, live_server
    ):
        page = regular_user_browser_context.new_page()
        page.goto(f"{live_server}/user/me", wait_until="networkidle")

        page.get_by_role("button", name="Delete account").click()
        submit = page.get_by_role("button", name="Delete my account")
        expect(submit).to_be_visible()
        expect(submit).to_be_disabled()

        page.locator('input[name="confirm_username"]').fill("e2e_regular")
        expect(submit).to_be_enabled()

        page.locator('input[name="confirm_username"]').fill("wrong")
        expect(submit).to_be_disabled()
        page.keyboard.press("Escape")


class TestNavbarMobileMenu:
    def test_hamburger_toggle_and_escape(self, admin_browser_context, live_server):
        page = admin_browser_context.new_page()
        page.set_viewport_size({"width": 500, "height": 800})
        page.goto(f"{live_server}/", wait_until="networkidle")

        toggle = page.get_by_label("Toggle navigation")
        expect(toggle).to_be_visible()
        panel = page.locator("#staff-nav-panel")
        expect(panel).not_to_be_visible()

        toggle.click()
        expect(panel).to_be_visible()
        page.keyboard.press("Escape")
        expect(panel).not_to_be_visible()


class TestOwnedPanelTradeableFlow:
    def test_add_then_toggle_trade_across_swaps(
        self, admin_browser_context, live_server, make_pin, db_handle
    ):
        pin = make_pin("OwnedPanelPin", tag_names=["owned-tag"])
        page = admin_browser_context.new_page()
        page.goto(f"{live_server}/get/pin/{pin['id']}", wait_until="networkidle")

        trigger = page.get_by_text("I Own", exact=False).first
        trigger.click()
        panel_content = page.locator(f"#owned-panel-content-{pin['id']}")
        expect(panel_content).to_be_visible()

        # Add one (htmx post → outerHTML swap of the panel content).
        with page.expect_response(
            lambda r: r.request.method == "POST" and "/user/pins/" in r.url
        ):
            panel_content.get_by_role("button", name="+ Add").first.click()
        expect(page.get_by_text("I Own (1)")).to_be_visible()

        rows = db_handle(
            "SELECT quantity, tradeable_quantity FROM user_owned_pins uop "
            "JOIN pins p ON p.id = uop.pin_id WHERE p.name = 'OwnedPanelPin'"
        )
        assert rows == [(1, 0)]

        # The swapped-in row must be interactive: toggle Trade → PATCH → swap.
        with page.expect_response(
            lambda r: r.request.method == "PATCH" and "/user/pins/" in r.url
        ):
            page.locator(
                f"#owned-panel-content-{pin['id']} input[type='checkbox']"
            ).first.check()
        rows = db_handle(
            "SELECT tradeable_quantity FROM user_owned_pins uop "
            "JOIN pins p ON p.id = uop.pin_id WHERE p.name = 'OwnedPanelPin'"
        )
        assert rows == [(1,)]

        # And the NEXT swapped-in generation too (swap-lifecycle acid test).
        with page.expect_response(
            lambda r: r.request.method == "PATCH" and "/user/pins/" in r.url
        ):
            page.locator(
                f"#owned-panel-content-{pin['id']} input[type='checkbox']"
            ).first.uncheck()
        rows = db_handle(
            "SELECT tradeable_quantity FROM user_owned_pins uop "
            "JOIN pins p ON p.id = uop.pin_id WHERE p.name = 'OwnedPanelPin'"
        )
        assert rows == [(0,)]
