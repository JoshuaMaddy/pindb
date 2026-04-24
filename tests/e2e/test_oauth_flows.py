"""E2E coverage of the OAuth signup / linking flow.

These tests use the in-app test-only OAuth provider (enabled by the
``ALLOW_TEST_OAUTH_PROVIDER`` env var set in ``live_server``) to sidestep
real Google/Discord/Meta endpoints.
"""

from __future__ import annotations

import uuid

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
class TestOAuthOnboarding:
    def test_first_time_oauth_signup_flows_through_onboarding(
        self, anon_browser_context, live_server, register_test_oauth_identity
    ):
        identity_id = f"e2e-{uuid.uuid4().hex[:8]}"
        register_test_oauth_identity(
            identity_id,
            provider="google",
            email=f"{identity_id}@example.com",
            username_hint=f"user_{identity_id}",
        )

        page = anon_browser_context.new_page()
        page.goto(f"{live_server}/auth/_test-oauth/start?identity_id={identity_id}")
        expect(page).to_have_url(f"{live_server}/auth/oauth/onboarding")
        expect(page.locator("h1")).to_contain_text("Finish signing up")

        username_input = page.locator("input[name='username']")
        expect(username_input).to_have_value(f"user_{identity_id}")
        page.click("button[type='submit']")
        page.wait_for_load_state("load")
        expect(page).to_have_url(f"{live_server}/")

    def test_returning_oauth_user_skips_onboarding(
        self, browser, live_server, register_test_oauth_identity, db_handle
    ):
        identity_id = f"e2e-{uuid.uuid4().hex[:8]}"
        register_test_oauth_identity(
            identity_id,
            provider="google",
            email=f"{identity_id}@example.com",
            username_hint=f"user_{identity_id}",
        )

        # First pass: create the account.
        context1 = browser.new_context(base_url=live_server)
        try:
            page = context1.new_page()
            page.goto(f"{live_server}/auth/_test-oauth/start?identity_id={identity_id}")
            page.wait_for_url(f"{live_server}/auth/oauth/onboarding")
            page.click("button[type='submit']")
            page.wait_for_url(f"{live_server}/")
        finally:
            context1.close()

        # Second pass: should go straight home.
        context2 = browser.new_context(base_url=live_server)
        try:
            page = context2.new_page()
            page.goto(f"{live_server}/auth/_test-oauth/start?identity_id={identity_id}")
            page.wait_for_load_state("load")
            expect(page).to_have_url(f"{live_server}/")
        finally:
            context2.close()

        rows = db_handle(
            "SELECT COUNT(*) FROM user_auth_providers WHERE provider_user_id = %s",
            (identity_id,),
        )
        assert rows[0][0] == 1


@pytest.mark.e2e
class TestProviderLinking:
    def test_password_user_links_then_signs_in_with_provider(
        self,
        regular_user_browser_context,
        live_server,
        register_test_oauth_identity,
        browser,
        db_handle,
    ):
        identity_id = f"e2e-{uuid.uuid4().hex[:8]}"
        register_test_oauth_identity(
            identity_id,
            provider="google",
            email="e2e_regular@x.test",
            username_hint="e2e_regular",
        )

        # Visit security page and click "link" via the start-link URL
        # (the button target is /auth/google?link=1, but with the test
        # provider we use /auth/_test-oauth/start?link=1).
        page = regular_user_browser_context.new_page()
        page.goto(
            f"{live_server}/auth/_test-oauth/start?identity_id={identity_id}&link=1"
        )
        page.wait_for_load_state("load")
        expect(page).to_have_url(f"{live_server}/user/me/security")

        rows = db_handle(
            "SELECT u.username FROM user_auth_providers p "
            "JOIN users u ON u.id = p.user_id "
            "WHERE p.provider_user_id = %s",
            (identity_id,),
        )
        assert rows and rows[0][0] == "e2e_regular"

        # Log out, then sign in with the provider — should land logged-in.
        context = browser.new_context(base_url=live_server)
        try:
            provider_page = context.new_page()
            provider_page.goto(
                f"{live_server}/auth/_test-oauth/start?identity_id={identity_id}"
            )
            provider_page.wait_for_load_state("load")
            expect(provider_page).to_have_url(f"{live_server}/")
        finally:
            context.close()
