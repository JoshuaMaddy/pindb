"""E2E password policy + change-password flow."""

from __future__ import annotations

import uuid

import pytest
from playwright.sync_api import expect

from tests.e2e._pages import submit_content_form


@pytest.mark.e2e
class TestSignupPasswordPolicy:
    def test_weak_password_blocked_on_signup(self, anon_browser_context, live_server):
        page = anon_browser_context.new_page()
        page.goto(f"{live_server}/auth/signup")
        page.fill("input[name='username']", f"weak_{uuid.uuid4().hex[:6]}")
        page.fill("input[name='email']", f"weak_{uuid.uuid4().hex[:6]}@example.com")
        page.fill("input[name='password']", "hunter2hunter2")
        page.click("button[type='submit']")
        page.wait_for_load_state("load")
        # Still on signup page; error bullet-list visible.
        expect(page).to_have_url(f"{live_server}/auth/signup")
        expect(page.locator("h1")).to_contain_text("Sign Up")

    def test_strong_password_accepted(self, anon_browser_context, live_server):
        handle = uuid.uuid4().hex[:8]
        page = anon_browser_context.new_page()
        page.goto(f"{live_server}/auth/signup")
        page.fill("input[name='username']", f"strong_{handle}")
        page.fill("input[name='email']", f"strong_{handle}@example.com")
        page.fill("input[name='password']", "Velvet-Orbit-Maple-42!")
        page.click("button[type='submit']")
        page.wait_for_load_state("load")
        expect(page).to_have_url(f"{live_server}/")


@pytest.mark.e2e
class TestChangePassword:
    def test_change_password_happy_path(self, anon_browser_context, live_server):
        # Create a fresh throwaway user so we don't risk bricking the
        # session-scoped regular user's password if the revert fails.
        username = f"e2e_pwchange_{uuid.uuid4().hex[:8]}"
        old_password = "Quartz-Nimbus-Plover-42!"
        new_password = "Velvet-Orbit-Maple-42!"

        page = anon_browser_context.new_page()
        page.goto(f"{live_server}/auth/signup")
        page.fill("input[name='username']", username)
        page.fill("input[name='email']", f"{username}@example.test")
        page.fill("input[name='password']", old_password)
        page.click("button[type='submit']")
        page.wait_for_load_state("load")

        page.goto(f"{live_server}/user/me/security")
        page.fill("input[name='current_password']", old_password)
        page.fill("input[name='new_password']", new_password)
        page.fill("input[name='confirm_password']", new_password)
        submit_content_form(page)
        expect(page).to_have_url(
            f"{live_server}/user/me/security?success=Password+updated"
        )
