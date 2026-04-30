"""Signup, login, and logout round-trip."""

from __future__ import annotations

from playwright.sync_api import expect


def test_signup_login_logout_flow(anon_browser_context, live_server):
    page = anon_browser_context.new_page()

    page.goto(f"{live_server}/auth/signup")
    page.fill("input[name='username']", "e2e_flow_user")
    page.fill("input[name='email']", "flow@example.test")
    page.fill("input[name='password']", "Quartz-Nimbus-Plover-42!")
    page.click("button[type='submit']")
    page.wait_for_load_state("load")

    page.locator("form[action='/auth/logout'] button[type='submit']").click()
    page.wait_for_load_state("load")
    page.goto(f"{live_server}/auth/login")
    page.fill("input[name='username']", "e2e_flow_user")
    page.fill("input[name='password']", "Quartz-Nimbus-Plover-42!")
    page.click("button[type='submit']")
    page.wait_for_load_state("load")

    page.goto(f"{live_server}/user/me")
    expect(page).to_have_url(f"{live_server}/user/e2e_flow_user", ignore_case=True)
