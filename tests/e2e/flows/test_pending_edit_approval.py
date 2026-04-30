"""Editor submits a pending edit; admin approves from the queue."""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from tests.e2e._pages import submit_content_form


@pytest.mark.slow
def test_editor_pending_edit_approved_by_admin(
    admin_browser_context, editor_browser_context, live_server
):
    admin_page = admin_browser_context.new_page()
    admin_page.goto(f"{live_server}/create/shop")
    admin_page.fill("input[name='name']", "Target Shop")
    submit_content_form(admin_page)

    editor_page = editor_browser_context.new_page()
    editor_page.goto(f"{live_server}/list/shops")
    editor_page.get_by_text("Target Shop").first.click()
    editor_page.wait_for_load_state("load")
    editor_page.locator("a[href*='/edit/shop/']").first.click()
    editor_page.wait_for_load_state("load")
    editor_page.fill("input[name='name']", "Target Shop (Renamed)")
    submit_content_form(editor_page)

    admin_page.goto(f"{live_server}/admin/pending")
    expect(admin_page.get_by_text("Target Shop")).to_be_visible()
    admin_page.locator(
        "form[action*='/admin/pending/approve-edits/shop/']"
    ).first.locator("button[type='submit']").click()
    admin_page.wait_for_load_state("load")

    admin_page.goto(f"{live_server}/list/shops")
    expect(admin_page.get_by_text("Target Shop (Renamed)")).to_be_visible()
