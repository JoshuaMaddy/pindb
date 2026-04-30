"""Admin creates a shop via the browser form."""

from __future__ import annotations

from playwright.sync_api import expect

from tests.e2e._pages import set_markdown_field, submit_content_form


def test_admin_creates_shop(admin_browser_context, live_server):
    page = admin_browser_context.new_page()
    page.goto(f"{live_server}/create/shop")
    page.fill("input[name='name']", "E2E Shop")
    set_markdown_field(page, "description", "Created via Playwright")
    submit_content_form(page)

    page.goto(f"{live_server}/list/shops")
    expect(page.get_by_text("E2E Shop")).to_be_visible()
