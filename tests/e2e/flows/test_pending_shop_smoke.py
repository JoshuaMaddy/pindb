"""Smoke: pending shop appears in queue and becomes public after approval."""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from tests.e2e._pages import submit_content_form


@pytest.mark.slow
def test_pending_shop_approve_smoke(
    admin_browser_context, editor_browser_context, live_server
):
    editor_page = editor_browser_context.new_page()
    editor_page.goto(f"{live_server}/create/shop")
    editor_page.fill("input[name='name']", "Cascade Shop")
    submit_content_form(editor_page)

    admin_page = admin_browser_context.new_page()
    admin_page.goto(f"{live_server}/admin/pending")
    expect(admin_page.get_by_text("Cascade Shop")).to_be_visible()

    admin_page.locator("form[action*='/admin/pending/approve/shop/']").first.locator(
        "button[type='submit']"
    ).click()
    admin_page.wait_for_load_state("load")

    with admin_browser_context.browser.new_context(base_url=live_server) as anon:
        anon_page = anon.new_page()
        anon_page.goto(f"{live_server}/list/shops")
        expect(anon_page.get_by_text("Cascade Shop")).to_be_visible()
