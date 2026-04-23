"""Browser-level checks of what the user actually sees.

These tests complement `test_flows.py` by asserting on visible page content,
navbar visibility rules, role-gated UI affordances, error states, and the
HTMX/Alpine wiring behind a few key interactions.

Run with:

    uv run pytest -m e2e tests/e2e/test_ui_content.py
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import expect

from tests.e2e._pages import set_markdown_field, submit_content_form

# Generous default — uvicorn cold-starts can be slow on Windows runners.
expect.set_options(timeout=10_000)


# ---------------------------------------------------------------------------
# Navbar / role-gated affordances
# ---------------------------------------------------------------------------


class TestNavbar:
    def test_anonymous_navbar_shows_login_and_hides_create_admin(
        self, browser, live_server
    ):
        context = browser.new_context(base_url=live_server)
        try:
            page = context.new_page()
            page.goto(f"{live_server}/")
            expect(page.get_by_role("link", name="Login")).to_be_visible()
            expect(page.get_by_role("link", name="PinDB")).to_be_visible()
            # Anonymous users do not see Create or Admin entry points.
            expect(page.locator("nav a[href='/create']")).to_have_count(0)
            expect(page.locator("nav a[href='/admin']")).to_have_count(0)
        finally:
            context.close()

    def test_admin_navbar_shows_create_and_admin(
        self, admin_browser_context, live_server
    ):
        page = admin_browser_context.new_page()
        page.goto(f"{live_server}/")
        # Staff nav renders its links twice (desktop + mobile panel); `.first`
        # pins to the visible desktop copy.
        expect(page.locator("nav a[href='/create']").first).to_be_visible()
        expect(page.locator("nav a[href='/admin']").first).to_be_visible()
        expect(page.locator("form[action='/auth/logout']")).to_be_visible()
        # Username link points at the admin's profile.
        expect(page.locator("nav a[href*='/user/']").first).to_be_visible()

    def test_editor_navbar_shows_create_but_not_admin(
        self, editor_browser_context, live_server
    ):
        page = editor_browser_context.new_page()
        page.goto(f"{live_server}/")
        expect(page.locator("nav a[href='/create']").first).to_be_visible()
        # Non-admin editor: no Admin link.
        expect(page.locator("nav a[href='/admin']")).to_have_count(0)


# ---------------------------------------------------------------------------
# Auth pages: error messaging
# ---------------------------------------------------------------------------


class TestAuthErrorMessages:
    def test_invalid_login_renders_error_message(self, browser, live_server):
        context = browser.new_context(base_url=live_server)
        try:
            page = context.new_page()
            page.goto(f"{live_server}/auth/login")
            page.fill("input[name='username']", "nope_no_user_here")
            page.fill("input[name='password']", "wrongpass")
            page.click("button[type='submit']")
            page.wait_for_load_state("load")
            expect(page).to_have_url(re.compile(r"/auth/login$"))
            expect(page.get_by_text("Invalid username or password.")).to_be_visible()
            # Login heading still present (we re-render the same form).
            expect(page.get_by_role("heading", name="Login")).to_be_visible()
        finally:
            context.close()

    def test_duplicate_signup_username_shows_error(self, browser, live_server):
        context = browser.new_context(base_url=live_server)
        try:
            page = context.new_page()
            # First signup succeeds.
            page.goto(f"{live_server}/auth/signup")
            page.fill("input[name='username']", "dupuser_e2e")
            page.fill("input[name='email']", "dupuser_e2e@example.test")
            page.fill("input[name='password']", "Quartz-Nimbus-Plover-42!")
            page.click("button[type='submit']")
            page.wait_for_load_state("load")

            # Logout then try to register the same username again.
            page.locator("form[action='/auth/logout'] button[type='submit']").click()
            page.wait_for_load_state("load")

            page.goto(f"{live_server}/auth/signup")
            page.fill("input[name='username']", "dupuser_e2e")
            page.fill("input[name='email']", "dupuser2_e2e@example.test")
            page.fill("input[name='password']", "Quartz-Nimbus-Plover-42!")
            page.click("button[type='submit']")
            page.wait_for_load_state("load")
            # Handler returns a unified clash message to avoid user/email
            # enumeration — not a specific "Username already taken." text.
            expect(
                page.get_by_text("Those sign-up details aren't available.")
            ).to_be_visible()
        finally:
            context.close()


# ---------------------------------------------------------------------------
# 404 pages
# ---------------------------------------------------------------------------


class TestNotFound:
    def test_missing_image_returns_404_in_browser(
        self, admin_browser_context, live_server
    ):
        page = admin_browser_context.new_page()
        # Navigate to a guaranteed-missing image GUID.
        response = page.goto(
            f"{live_server}/get/image/00000000-0000-0000-0000-000000000000"
        )
        assert response is not None
        assert response.status == 404

    def test_edit_missing_shop_returns_404(self, admin_browser_context, live_server):
        page = admin_browser_context.new_page()
        response = page.goto(f"{live_server}/edit/shop/9999999")
        assert response is not None
        assert response.status == 404


# ---------------------------------------------------------------------------
# Pending approval queue: visible content + counts + empty state
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestPendingQueueContent:
    def test_editor_submission_appears_in_admin_queue_with_metadata(
        self, admin_browser_context, editor_browser_context, live_server
    ):
        # Editor creates a pending shop.
        editor_page = editor_browser_context.new_page()
        editor_page.goto(f"{live_server}/create/shop")
        editor_page.fill("input[name='name']", "Queued Shop")
        set_markdown_field(editor_page, "description", "Pending review by an admin.")
        submit_content_form(editor_page)

        # Admin queue page renders heading, "Shops" section, and the row.
        admin_page = admin_browser_context.new_page()
        admin_page.goto(f"{live_server}/admin/pending")
        expect(
            admin_page.get_by_role("heading", name="Pending Approvals")
        ).to_be_visible()
        expect(admin_page.get_by_role("heading", name="Shops")).to_be_visible()

        # The row should link to the entity's detail page and show the
        # editor's username in the "Submitted by" column.
        row = admin_page.locator("tr", has_text="Queued Shop")
        expect(row).to_be_visible()
        # Editor login created a `e2e_editor_pw` user via the fixture.
        expect(row).to_contain_text("e2e_editor_pw")
        # Approve / Reject / Delete buttons are present in this row.
        expect(row.get_by_role("button", name="Approve")).to_be_visible()
        expect(row.get_by_role("button", name="Reject")).to_be_visible()
        expect(row.get_by_role("button", name="Delete")).to_be_visible()


# ---------------------------------------------------------------------------
# Pending edit banner on canonical entity views
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestPendingEditBanner:
    def test_canonical_shop_view_shows_pending_edit_banner_to_admin(
        self, admin_browser_context, editor_browser_context, live_server
    ):
        # Admin creates an approved shop.
        admin_page = admin_browser_context.new_page()
        admin_page.goto(f"{live_server}/create/shop")
        admin_page.fill("input[name='name']", "BannerTarget")
        submit_content_form(admin_page)
        admin_page.wait_for_load_state("load")

        # Editor edits it → creates a pending edit (no canonical change).
        editor_page = editor_browser_context.new_page()
        editor_page.goto(f"{live_server}/list/shops")
        editor_page.get_by_text("BannerTarget").first.click()
        editor_page.wait_for_load_state("load")
        editor_page.locator("a[href*='/edit/shop/']").first.click()
        editor_page.wait_for_load_state("load")
        editor_page.fill("input[name='name']", "BannerTarget (edited)")
        submit_content_form(editor_page)
        editor_page.wait_for_load_state("load")

        # Admin visits the canonical detail page and sees the banner.
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
        # Setup: admin creates a shop, editor edits it.
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

        # Anonymous viewer never sees the banner.
        with browser.new_context(base_url=live_server) as anon:
            anon_page = anon.new_page()
            anon_page.goto(f"{live_server}/list/shops")
            anon_page.get_by_text("AnonShopBanner").first.click()
            anon_page.wait_for_load_state("load")
            expect(anon_page.locator("body")).not_to_contain_text(
                "This entry has a pending edit awaiting approval."
            )


# ---------------------------------------------------------------------------
# Editor edit-shop reject flow: rejected edit is removed from queue
# ---------------------------------------------------------------------------


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

        # Admin rejects the edit.
        admin_page.goto(f"{live_server}/admin/pending")
        admin_page.locator(
            "form[action*='/admin/pending/reject-edits/shop/']"
        ).first.locator("button[type='submit']").click()
        admin_page.wait_for_load_state("load")

        # Canonical name unchanged on the public list.
        admin_page.goto(f"{live_server}/list/shops")
        expect(admin_page.get_by_text("RejectMe")).to_be_visible()
        expect(admin_page.get_by_text("RejectMe (renamed)")).to_have_count(0)


# ---------------------------------------------------------------------------
# Theme switching: HTMX-driven, no page reload, html className updates
# ---------------------------------------------------------------------------


class TestThemeSwitcher:
    def test_changing_theme_updates_html_class_without_reload(
        self, admin_browser_context, live_server
    ):
        page = admin_browser_context.new_page()
        page.goto(f"{live_server}/user/me", wait_until="load")

        # Default theme is mocha.
        expect(page.locator("html")).to_have_attribute(
            "class", re.compile(r"\bmocha\b")
        )

        # Pick a different theme — radios are visually hidden but still clickable.
        target = page.locator("input[name='theme'][value='dracula']").first
        expect(target).to_have_count(1)
        target.check(force=True)
        # Wait for the HTMX request to settle.
        page.wait_for_load_state("load")

        expect(page.locator("html")).to_have_attribute(
            "class", re.compile(r"\bdracula\b")
        )

        # Reload the page; persisted preference should still apply.
        page.reload(wait_until="load")
        expect(page.locator("html")).to_have_attribute(
            "class", re.compile(r"\bdracula\b")
        )


# ---------------------------------------------------------------------------
# Anonymous protected-route redirects / forbiddens
# ---------------------------------------------------------------------------


class TestAuthGuards:
    def test_anonymous_get_create_shop_is_forbidden(self, browser, live_server):
        context = browser.new_context(base_url=live_server)
        try:
            page = context.new_page()
            response = page.goto(f"{live_server}/create/shop")
            assert response is not None
            # Editor-required routes return 403 to anonymous (FastAPI Depends raises).
            assert response.status in (401, 403)
        finally:
            context.close()

    def test_anonymous_admin_panel_is_forbidden(self, browser, live_server):
        context = browser.new_context(base_url=live_server)
        try:
            page = context.new_page()
            response = page.goto(f"{live_server}/admin")
            assert response is not None
            assert response.status in (401, 403)
        finally:
            context.close()

    def test_editor_admin_panel_is_forbidden(self, editor_browser_context, live_server):
        page = editor_browser_context.new_page()
        response = page.goto(f"{live_server}/admin")
        assert response is not None
        assert response.status == 403


# ---------------------------------------------------------------------------
# Page titles + headings on top-level pages
# ---------------------------------------------------------------------------


class TestPageTitles:
    @pytest.mark.parametrize(
        ("path", "title_suffix"),
        [
            ("/", "Home | PinDB"),
            ("/auth/login", "Login | PinDB"),
            ("/auth/signup", "Sign Up | PinDB"),
            ("/list/shops", "Shops | PinDB"),
            ("/search/pin", "Search for a Pin | PinDB"),
        ],
    )
    def test_top_level_pages_have_expected_titles(
        self, browser, live_server, path, title_suffix
    ):
        context = browser.new_context(base_url=live_server)
        try:
            page = context.new_page()
            page.goto(f"{live_server}{path}")
            expect(page).to_have_title(title_suffix)
        finally:
            context.close()

    def test_admin_pending_queue_title_for_admin(
        self, admin_browser_context, live_server
    ):
        page = admin_browser_context.new_page()
        page.goto(f"{live_server}/admin/pending")
        expect(page).to_have_title("Pending Approvals | PinDB")


# ---------------------------------------------------------------------------
# Empty state on admin pending queue
# ---------------------------------------------------------------------------


class TestPendingQueueEmptyState:
    def test_pending_queue_renders_when_visited(
        self, admin_browser_context, live_server
    ):
        # We can't guarantee global emptiness across tests sharing the live
        # server, but the heading and explanation paragraph should always
        # render for an admin viewer.
        page = admin_browser_context.new_page()
        page.goto(f"{live_server}/admin/pending")
        expect(page.get_by_role("heading", name="Pending Approvals")).to_be_visible()
        expect(
            page.get_by_text(
                "Review and approve or reject pending entries", exact=False
            )
        ).to_be_visible()
