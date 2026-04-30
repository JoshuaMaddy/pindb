"""Pending-edit banner and reject flow (Playwright)."""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import expect

from tests.e2e._pages import submit_content_form


@pytest.mark.slow
class TestPendingEditBanner:
    def test_canonical_shop_view_shows_pending_edit_banner_to_admin(
        self, admin_browser_context, editor_browser_context, live_server
    ):
        admin_page = admin_browser_context.new_page()
        admin_page.goto(f"{live_server}/create/shop")
        admin_page.fill("input[name='name']", "BannerTarget")
        submit_content_form(admin_page)
        admin_page.wait_for_load_state("load")

        editor_page = editor_browser_context.new_page()
        editor_page.goto(f"{live_server}/list/shops")
        editor_page.get_by_text("BannerTarget").first.click()
        editor_page.wait_for_load_state("load")
        editor_page.locator("a[href*='/edit/shop/']").first.click()
        editor_page.wait_for_load_state("load")
        editor_page.fill("input[name='name']", "BannerTarget (edited)")
        submit_content_form(editor_page)
        editor_page.wait_for_load_state("load")

        admin_page.goto(f"{live_server}/list/shops")
        admin_page.get_by_text("BannerTarget", exact=False).first.click()
        admin_page.wait_for_load_state("load")
        expect(
            admin_page.get_by_text("This entry has a pending edit awaiting approval.")
        ).to_be_visible()
        expect(
            admin_page.get_by_role("link", name=re.compile("View pending"))
        ).to_be_visible()

    def test_anonymous_user_does_not_see_pending_edit_banner(
        self, browser, admin_browser_context, editor_browser_context, live_server
    ):
        admin_page = admin_browser_context.new_page()
        admin_page.goto(f"{live_server}/create/shop")
        admin_page.fill("input[name='name']", "AnonShopBanner")
        submit_content_form(admin_page)
        admin_page.wait_for_load_state("load")

        editor_page = editor_browser_context.new_page()
        editor_page.goto(f"{live_server}/list/shops")
        editor_page.get_by_text("AnonShopBanner").first.click()
        editor_page.wait_for_load_state("load")
        editor_page.locator("a[href*='/edit/shop/']").first.click()
        editor_page.wait_for_load_state("load")
        editor_page.fill("input[name='name']", "AnonShopBanner (e)")
        submit_content_form(editor_page)
        editor_page.wait_for_load_state("load")

        with browser.new_context(base_url=live_server) as anon:
            anon_page = anon.new_page()
            anon_page.goto(f"{live_server}/list/shops")
            anon_page.get_by_text("AnonShopBanner").first.click()
            anon_page.wait_for_load_state("load")
            expect(anon_page.locator("body")).not_to_contain_text(
                "This entry has a pending edit awaiting approval."
            )


@pytest.mark.slow
class TestPendingEditReject:
    def test_admin_reject_removes_edit_from_queue_and_keeps_canonical(
        self, admin_browser_context, editor_browser_context, live_server
    ):
        admin_page = admin_browser_context.new_page()
        admin_page.goto(f"{live_server}/create/shop")
        admin_page.fill("input[name='name']", "RejectMe")
        submit_content_form(admin_page)
        admin_page.wait_for_load_state("load")

        editor_page = editor_browser_context.new_page()
        editor_page.goto(f"{live_server}/list/shops")
        editor_page.get_by_text("RejectMe").first.click()
        editor_page.wait_for_load_state("load")
        editor_page.locator("a[href*='/edit/shop/']").first.click()
        editor_page.wait_for_load_state("load")
        editor_page.fill("input[name='name']", "RejectMe (renamed)")
        submit_content_form(editor_page)
        editor_page.wait_for_load_state("load")

        admin_page.goto(f"{live_server}/admin/pending")
        admin_page.locator(
            "form[action*='/admin/pending/reject-edits/shop/']"
        ).first.locator("button[type='submit']").click()
        admin_page.wait_for_load_state("load")

        admin_page.goto(f"{live_server}/list/shops")
        expect(admin_page.get_by_text("RejectMe")).to_be_visible()
        expect(admin_page.get_by_text("RejectMe (renamed)")).to_have_count(0)
