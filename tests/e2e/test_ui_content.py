"""Browser-level checks of what the user actually sees.

These tests complement `test_flows.py` by asserting on visible page content,
navbar visibility rules, role-gated UI affordances, error states, and the
HTMX/Alpine wiring behind a few key interactions.

Pure-assertion checks (navbar visibility, page titles, auth guards, 404s)
drive the live server over HTTP + BeautifulSoup — full Playwright browsers
aren't needed to confirm that HTML the server renders contains / excludes
specific elements. This keeps the browser surface for the tests that
actually need DOM interactions (HTMX banners, Alpine toggles, form flows).

Run with:

    uv run pytest -m e2e tests/e2e/test_ui_content.py
"""

from __future__ import annotations

import re

import pytest
from bs4 import BeautifulSoup
from playwright.sync_api import expect

from tests.e2e._pages import set_markdown_field, submit_content_form


def _soup(response) -> BeautifulSoup:
    return BeautifulSoup(response.text, "html.parser")


# ---------------------------------------------------------------------------
# Navbar / role-gated affordances (httpx — server-rendered links only)
# ---------------------------------------------------------------------------


class TestNavbar:
    def test_anonymous_navbar_shows_login_and_hides_create_admin(
        self, anon_http_client
    ):
        response = anon_http_client.get("/")
        assert response.status_code == 200
        soup = _soup(response)
        nav_links = {a.get_text(strip=True): a for a in soup.select("nav a")}
        # Anonymous users see the Login link but not Create/Admin.
        assert "Login" in nav_links
        assert soup.select_one('a:-soup-contains("PinDB")') is not None
        assert soup.select_one('nav a[href="/create"]') is None
        assert soup.select_one('nav a[href="/admin"]') is None

    def test_admin_navbar_shows_create_and_admin(self, admin_http_client):
        response = admin_http_client.get("/")
        assert response.status_code == 200
        soup = _soup(response)
        assert soup.select_one('nav a[href="/create"]') is not None
        assert soup.select_one('nav a[href="/admin"]') is not None
        # Logout form present and a /user/... profile link.
        assert soup.select_one('form[action="/auth/logout"]') is not None
        assert soup.select_one('nav a[href^="/user/"]') is not None

    def test_editor_navbar_shows_create_but_not_admin(self, editor_http_client):
        response = editor_http_client.get("/")
        assert response.status_code == 200
        soup = _soup(response)
        assert soup.select_one('nav a[href="/create"]') is not None
        # Non-admin editor: no Admin link.
        assert soup.select_one('nav a[href="/admin"]') is None


# ---------------------------------------------------------------------------
# Auth pages: error messaging
# ---------------------------------------------------------------------------


class TestAuthErrorMessages:
    def test_invalid_login_renders_error_message(self, anon_http_client):
        # Follow the POST's re-render (not a redirect on failure).
        response = anon_http_client.post(
            "/auth/login",
            data={"username": "nope_no_user_here", "password": "wrongpass"},
        )
        # Failed login re-renders the form with a 401 status, not a 200 +
        # redirect.
        assert response.status_code == 401
        soup = _soup(response)
        assert "Invalid username or password." in soup.get_text()
        # Login heading still present (form re-rendered).
        headings = [h.get_text(strip=True) for h in soup.select("h1")]
        assert "Login" in headings

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
    def test_missing_image_returns_404(self, admin_http_client):
        response = admin_http_client.get(
            "/get/image/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    def test_edit_missing_shop_returns_404(self, admin_http_client):
        response = admin_http_client.get("/edit/shop/9999999")
        assert response.status_code == 404


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
        self, regular_user_browser_context, live_server, db_handle
    ):
        # Use the regular user (not admin); revert the theme change at the
        # end so this test's flip doesn't leak into later tests that read
        # the default theme.
        page = regular_user_browser_context.new_page()
        try:
            page.goto(f"{live_server}/user/me", wait_until="load")

            # Default theme is mocha.
            expect(page.locator("html")).to_have_attribute(
                "class", re.compile(r"\bmocha\b")
            )

            # Pick a different theme — radios are visually hidden. ``check(force=True)``
            # does not always dispatch ``change``, which HTMX listens for; fire it explicitly.
            target = page.locator("input[name='theme'][value='dracula']").first
            expect(target).to_have_count(1)
            with page.expect_response(
                lambda r: r.request.method == "POST" and "/user/me/settings" in r.url
            ):
                target.check(force=True)
                target.dispatch_event("change")
            page.wait_for_load_state("load")

            expect(page.locator("html")).to_have_attribute(
                "class", re.compile(r"\bdracula\b")
            )

            # Reload the page; persisted preference should still apply.
            page.reload(wait_until="load")
            expect(page.locator("html")).to_have_attribute(
                "class", re.compile(r"\bdracula\b")
            )
        finally:
            # Revert directly in the DB: the session-scoped regular user
            # survives across tests, so any default-theme assertion in a
            # later test would otherwise see the leaked value.
            db_handle(
                "UPDATE users SET theme = 'mocha', dimension_unit = 'mm' "
                "WHERE username = 'e2e_regular'"
            )


# ---------------------------------------------------------------------------
# Anonymous protected-route redirects / forbiddens
# ---------------------------------------------------------------------------


class TestAuthGuards:
    def test_anonymous_get_create_shop_is_forbidden(self, anon_http_client):
        # Editor-required routes return 401/403 to anonymous.
        response = anon_http_client.get("/create/shop")
        assert response.status_code in (401, 403)

    def test_anonymous_admin_panel_is_forbidden(self, anon_http_client):
        response = anon_http_client.get("/admin")
        assert response.status_code in (401, 403)

    def test_editor_admin_panel_is_forbidden(self, editor_http_client):
        response = editor_http_client.get("/admin")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Page titles + headings on top-level pages
# ---------------------------------------------------------------------------


class TestPageTitles:
    @pytest.mark.parametrize(
        ("path", "expected_title"),
        [
            ("/", "Home | PinDB"),
            ("/auth/login", "Login | PinDB"),
            ("/auth/signup", "Sign Up | PinDB"),
            ("/list/shops", "Shops | PinDB"),
            ("/search/pin", "Search for a Pin | PinDB"),
        ],
    )
    def test_top_level_pages_have_expected_titles(
        self, anon_http_client, path, expected_title
    ):
        response = anon_http_client.get(path)
        assert response.status_code == 200
        soup = _soup(response)
        assert soup.title is not None
        assert soup.title.string == expected_title

    def test_admin_pending_queue_title_for_admin(self, admin_http_client):
        response = admin_http_client.get("/admin/pending")
        assert response.status_code == 200
        soup = _soup(response)
        assert soup.title is not None
        assert soup.title.string == "Pending Approvals | PinDB"


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
