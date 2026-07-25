"""E2E password policy on admin-created accounts + the change-password flow."""

from __future__ import annotations

import uuid

import pytest
from playwright.sync_api import expect

from tests.e2e._pages import submit_content_form
from tests.fixtures.e2e_users import ADMIN


@pytest.mark.e2e
class TestAdminCreatePasswordPolicy:
    """Signup is gone; the policy now guards the admin create-user form."""

    def test_weak_password_blocked(self, admin_http_client):
        handle = uuid.uuid4().hex[:8]
        response = admin_http_client.post(
            "/admin/users/create",
            data={
                "username": f"weak_{handle}",
                "email": f"weak_{handle}@example.com",
                "password": "hunter2hunter2",
            },
        )
        assert response.status_code == 400
        assert "password" in response.text.lower()

    def test_strong_password_accepted(self, admin_http_client):
        handle = uuid.uuid4().hex[:8]
        response = admin_http_client.post(
            "/admin/users/create",
            data={
                "username": f"strong_{handle}",
                "email": f"strong_{handle}@example.com",
                "password": "Velvet-Orbit-Maple-42!",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303


@pytest.mark.e2e
class TestChangePassword:
    def test_change_password_happy_path(
        self, admin_http_client, anon_browser_context, live_server
    ):
        # Create a throwaway user through the admin form so a failed revert
        # cannot brick the session-scoped cast's passwords.
        username = f"e2e_pwchange_{uuid.uuid4().hex[:8]}"
        old_password = "Quartz-Nimbus-Plover-42!"
        new_password = "Velvet-Orbit-Maple-42!"

        created = admin_http_client.post(
            "/admin/users/create",
            data={
                "username": username,
                "email": f"{username}@example.test",
                "password": old_password,
            },
            follow_redirects=False,
        )
        assert created.status_code == 303, created.text[:300]

        page = anon_browser_context.new_page()
        page.goto(f"{live_server}/auth/login")
        page.fill("input[name='username']", username)
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

    def test_admin_can_still_log_in_after_creating_users(
        self, anon_browser_context, live_server
    ):
        page = anon_browser_context.new_page()
        page.goto(f"{live_server}/auth/login")
        page.fill("input[name='username']", ADMIN.username)
        page.fill("input[name='password']", ADMIN.password)
        page.click("button[type='submit']")
        page.wait_for_load_state("load")
        expect(page).to_have_url(f"{live_server}/")
