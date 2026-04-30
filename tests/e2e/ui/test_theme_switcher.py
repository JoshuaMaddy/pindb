"""Theme preference HTMX flow."""

from __future__ import annotations

import re

from playwright.sync_api import expect


class TestThemeSwitcher:
    def test_changing_theme_updates_html_class_without_reload(
        self, regular_user_browser_context, live_server, db_handle
    ):
        page = regular_user_browser_context.new_page()
        try:
            page.goto(f"{live_server}/user/me", wait_until="load")

            expect(page.locator("html")).to_have_attribute(
                "class", re.compile(r"\bmocha\b")
            )

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

            page.reload(wait_until="load")
            expect(page.locator("html")).to_have_attribute(
                "class", re.compile(r"\bdracula\b")
            )
        finally:
            db_handle(
                "UPDATE users SET theme = 'mocha', dimension_unit = 'mm' "
                "WHERE username = 'e2e_regular'"
            )
