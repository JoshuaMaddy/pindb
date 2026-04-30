"""Login/signup error rendering."""

from __future__ import annotations

from playwright.sync_api import expect

from tests.e2e.ui.http import parse_html as _soup


class TestAuthErrorMessages:
    def test_invalid_login_renders_error_message(self, anon_http_client):
        response = anon_http_client.post(
            "/auth/login",
            data={"username": "nope_no_user_here", "password": "wrongpass"},
        )
        assert response.status_code == 401
        soup = _soup(response)
        assert "Invalid username or password." in soup.get_text()
        headings = [h.get_text(strip=True) for h in soup.select("h1")]
        assert "Login" in headings

    def test_duplicate_signup_username_shows_error(self, browser, live_server):
        context = browser.new_context(base_url=live_server)
        try:
            page = context.new_page()
            page.goto(f"{live_server}/auth/signup")
            page.fill("input[name='username']", "dupuser_e2e")
            page.fill("input[name='email']", "dupuser_e2e@example.test")
            page.fill("input[name='password']", "Quartz-Nimbus-Plover-42!")
            page.click("button[type='submit']")
            page.wait_for_load_state("load")

            page.locator("form[action='/auth/logout'] button[type='submit']").click()
            page.wait_for_load_state("load")

            page.goto(f"{live_server}/auth/signup")
            page.fill("input[name='username']", "dupuser_e2e")
            page.fill("input[name='email']", "dupuser2_e2e@example.test")
            page.fill("input[name='password']", "Quartz-Nimbus-Plover-42!")
            page.click("button[type='submit']")
            page.wait_for_load_state("load")
            expect(
                page.get_by_text("Those sign-up details aren't available.")
            ).to_be_visible()
        finally:
            context.close()
