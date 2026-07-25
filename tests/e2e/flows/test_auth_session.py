"""Login and logout round-trip, plus the gate that forces login in the first place.

There is no signup to round-trip through any more — accounts are admin-created —
so this drives the real login form with a seeded account.
"""

from __future__ import annotations

from playwright.sync_api import expect

from tests.fixtures.e2e_users import REGULAR


def test_anonymous_visit_is_redirected_to_login(anon_browser_context, live_server):
    page = anon_browser_context.new_page()
    page.goto(f"{live_server}/list/tags")
    expect(page).to_have_url(f"{live_server}/auth/login?next=%2Flist%2Ftags")
    expect(page.locator("h1")).to_have_text("Login")


def test_login_logout_flow(anon_browser_context, live_server):
    page = anon_browser_context.new_page()

    page.goto(f"{live_server}/auth/login")
    page.fill("input[name='username']", REGULAR.username)
    page.fill("input[name='password']", REGULAR.password)
    page.click("button[type='submit']")
    page.wait_for_load_state("load")

    page.goto(f"{live_server}/user/me")
    expect(page).to_have_url(f"{live_server}/user/{REGULAR.username}", ignore_case=True)

    page.locator("form[action='/auth/logout'] button[type='submit']").click()
    page.wait_for_load_state("load")
    expect(page).to_have_url(f"{live_server}/auth/login")

    # The session is really gone: the gate turns a catalog page back into login.
    page.goto(f"{live_server}/list/tags")
    expect(page).to_have_url(f"{live_server}/auth/login?next=%2Flist%2Ftags")


def test_login_returns_to_the_requested_page(anon_browser_context, live_server):
    page = anon_browser_context.new_page()
    page.goto(f"{live_server}/list/tags")
    page.fill("input[name='username']", REGULAR.username)
    page.fill("input[name='password']", REGULAR.password)
    page.click("button[type='submit']")
    page.wait_for_load_state("load")
    expect(page).to_have_url(f"{live_server}/list/tags")


def test_login_page_offers_no_signup_or_oauth(anon_browser_context, live_server):
    page = anon_browser_context.new_page()
    page.goto(f"{live_server}/auth/login")
    expect(page.get_by_role("link", name="Sign up")).to_have_count(0)
    for provider in ("Google", "Discord", "Meta"):
        expect(page.get_by_text(f"Continue with {provider}")).to_have_count(0)
