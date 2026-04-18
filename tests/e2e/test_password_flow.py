"""E2E password policy + change-password flow."""

from __future__ import annotations

import uuid

import pytest
from playwright.sync_api import expect

from tests.e2e._pages import submit_content_form


@pytest.mark.e2e
class TestSignupPasswordPolicy:
    def test_weak_password_blocked_on_signup(self, browser, live_server):
        context = browser.new_context(base_url=live_server)
        try:
            page = context.new_page()
            page.goto(f"{live_server}/auth/signup")
            page.fill("input[name='username']", f"weak_{uuid.uuid4().hex[:6]}")
            page.fill("input[name='email']", f"weak_{uuid.uuid4().hex[:6]}@example.com")
            page.fill("input[name='password']", "hunter2hunter2")
            page.click("button[type='submit']")
            page.wait_for_load_state("load")
            # Still on signup page; error bullet-list visible.
            expect(page).to_have_url(f"{live_server}/auth/signup")
            expect(page.locator("h1")).to_contain_text("Sign Up")
        finally:
            context.close()

    def test_strong_password_accepted(self, browser, live_server):
        context = browser.new_context(base_url=live_server)
        try:
            handle = uuid.uuid4().hex[:8]
            page = context.new_page()
            page.goto(f"{live_server}/auth/signup")
            page.fill("input[name='username']", f"strong_{handle}")
            page.fill("input[name='email']", f"strong_{handle}@example.com")
            page.fill("input[name='password']", "Velvet-Orbit-Maple-42!")
            page.click("button[type='submit']")
            page.wait_for_load_state("load")
            expect(page).to_have_url(f"{live_server}/")
        finally:
            context.close()


@pytest.mark.e2e
class TestChangePassword:
    def test_change_password_happy_path(
        self, regular_user_browser_context, live_server
    ):
        page = regular_user_browser_context.new_page()
        page.goto(f"{live_server}/user/me/security")
        page.fill("input[name='current_password']", "E2e-Regular-Secret-9!")
        page.fill("input[name='new_password']", "Velvet-Orbit-Maple-42!")
        page.fill("input[name='confirm_password']", "Velvet-Orbit-Maple-42!")
        submit_content_form(page)
        # We land back on security with ?success= query string.
        expect(page).to_have_url(
            f"{live_server}/user/me/security?success=Password+updated"
        )

        # Revert so other tests keep working.
        page.fill("input[name='current_password']", "Velvet-Orbit-Maple-42!")
        page.fill("input[name='new_password']", "E2e-Regular-Secret-9!")
        page.fill("input[name='confirm_password']", "E2e-Regular-Secret-9!")
        submit_content_form(page)
