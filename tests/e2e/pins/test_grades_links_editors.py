"""Grades + links editors: behavior contract for the Alpine → Svelte port.

Written against the legacy Alpine implementation first (lockstep protocol);
the same assertions must pass unchanged after the island port. Selectors
deliberately use only the stable contract: input names (``grade_names``,
``grade_prices``, ``links``), button text, ``#pin-grade-section``, and the
``remove-grade-button`` / ``remove-link-button`` classes.
"""

from __future__ import annotations

from playwright.sync_api import expect

_GRADE_NAMES = 'input[name="grade_names"]'
_GRADE_PRICES = 'input[name="grade_prices"]'
_LINKS = 'input[name="links"]'


class TestGradesEditor:
    def test_add_and_remove_rows(self, admin_browser_context, live_server):
        page = admin_browser_context.new_page()
        page.goto(f"{live_server}/create/pin", wait_until="networkidle")

        rows = page.locator(_GRADE_NAMES)
        expect(rows).to_have_count(1)
        expect(rows.first).to_have_value("Normal")
        # Sole row: no visible remove button (Alpine hides it, Svelte omits it).
        expect(page.locator(".remove-grade-button:visible")).to_have_count(0)

        page.get_by_role("button", name="Add Grade").click()
        expect(rows).to_have_count(2)
        expect(page.locator(".remove-grade-button").first).to_be_visible()

        rows.nth(1).fill("Jumbo")
        page.locator(_GRADE_PRICES).nth(1).fill("12.50")

        page.locator(".remove-grade-button").nth(1).click()
        expect(rows).to_have_count(1)
        expect(rows.first).to_have_value("Normal")

    def test_reload_restores_grades(self, admin_browser_context, live_server):
        # NOTE: encodes the FIXED contract. Legacy form_persist restore was dead
        # code (alpine:initialized fired before its listener registered) and
        # saving only armed on reload-type loads; the island port repairs both.
        page = admin_browser_context.new_page()
        page.goto(f"{live_server}/create/pin", wait_until="networkidle")

        page.locator(_GRADE_NAMES).first.fill("Jumbo")
        page.locator(_GRADE_PRICES).first.fill("12.5")
        page.get_by_role("button", name="Add Grade").click()
        page.locator(_GRADE_NAMES).nth(1).fill("Mini")
        page.locator(_GRADE_PRICES).nth(1).fill("3")
        # Let the debounced form-persist save (300ms) flush.
        page.wait_for_timeout(500)

        page.reload(wait_until="networkidle")

        rows = page.locator(_GRADE_NAMES)
        expect(rows).to_have_count(2)
        expect(rows.nth(0)).to_have_value("Jumbo")
        expect(rows.nth(1)).to_have_value("Mini")
        expect(page.locator(_GRADE_PRICES).nth(0)).to_have_value("12.5")
        expect(page.locator(_GRADE_PRICES).nth(1)).to_have_value("3")

    def test_edit_submit_roundtrip(
        self, admin_browser_context, live_server, make_pin, db_handle
    ):
        pin = make_pin("GradeRoundTripPin", tag_names=["gradert-tag"])
        page = admin_browser_context.new_page()
        page.goto(f"{live_server}/edit/pin/{pin['id']}", wait_until="networkidle")

        rows = page.locator(_GRADE_NAMES)
        expect(rows.first).to_have_value("standard")

        page.get_by_role("button", name="Add Grade").click()
        rows.nth(1).fill("Jumbo")
        page.locator(_GRADE_PRICES).nth(1).fill("12.50")

        with page.expect_response(
            lambda r: r.request.method == "POST" and f"/edit/pin/{pin['id']}" in r.url
        ) as response_info:
            page.locator("#pin-form-submit").click()
        assert response_info.value.status < 400

        grades = db_handle(
            "SELECT g.name, g.price FROM grades g "
            "JOIN pins_grades pg ON g.id = pg.grade_id WHERE pg.pin_id = %s "
            "ORDER BY g.name",
            (pin["id"],),
        )
        assert [(name, price) for name, price in grades] == [
            ("Jumbo", 12.5),
            ("standard", None),
        ]

    def test_grades_visual_baseline(
        self, admin_browser_context, live_server, assert_screenshot
    ):
        page = admin_browser_context.new_page()
        page.goto(f"{live_server}/create/pin", wait_until="networkidle")
        page.get_by_role("button", name="Add Grade").click()
        page.locator(_GRADE_NAMES).nth(1).fill("Jumbo")
        page.locator(_GRADE_PRICES).nth(1).fill("12.50")
        assert_screenshot(
            page.locator("#pin-grade-section"),
            "grades-editor-two-rows",
        )


class TestLinksEditor:
    def test_add_remove_and_submit_roundtrip(
        self, admin_browser_context, live_server, db_handle
    ):
        page = admin_browser_context.new_page()
        page.goto(f"{live_server}/create/artist", wait_until="networkidle")

        links = page.locator(_LINKS)
        expect(links).to_have_count(1)
        expect(page.locator(".remove-link-button:visible")).to_have_count(0)

        page.get_by_role("button", name="Add Another Link").click()
        expect(links).to_have_count(2)
        links.nth(0).fill("https://example.com/a")
        links.nth(1).fill("https://example.com/b")

        # Third row, then remove it — count and values must survive.
        page.get_by_role("button", name="Add Another Link").click()
        links.nth(2).fill("https://example.com/c")
        page.locator(".remove-link-button").nth(2).click()
        expect(links).to_have_count(2)
        expect(links.nth(1)).to_have_value("https://example.com/b")

        page.locator('input[name="name"]').fill("LinksEditorArtist")
        with page.expect_response(
            lambda r: r.request.method == "POST" and "/create/artist" in r.url
        ) as response_info:
            page.locator("#simple-entity-submit").click()
        assert response_info.value.status < 400

        stored = db_handle(
            "SELECT l.path FROM links l "
            "JOIN artists_links al ON l.id = al.link_id "
            "JOIN artists a ON a.id = al.artist_id WHERE a.name = %s "
            "ORDER BY l.path",
            ("LinksEditorArtist",),
        )
        assert [path for (path,) in stored] == [
            "https://example.com/a",
            "https://example.com/b",
        ]

    def test_reload_restores_links(self, admin_browser_context, live_server):
        # Encodes the fixed contract — see grades reload test note.
        page = admin_browser_context.new_page()
        page.goto(f"{live_server}/create/artist", wait_until="networkidle")

        page.locator(_LINKS).first.fill("https://example.com/keep")
        page.get_by_role("button", name="Add Another Link").click()
        page.locator(_LINKS).nth(1).fill("https://example.com/also")
        page.wait_for_timeout(500)

        page.reload(wait_until="networkidle")

        links = page.locator(_LINKS)
        expect(links).to_have_count(2)
        expect(links.nth(0)).to_have_value("https://example.com/keep")
        expect(links.nth(1)).to_have_value("https://example.com/also")

    def test_links_visual_baseline(
        self, admin_browser_context, live_server, assert_screenshot
    ):
        page = admin_browser_context.new_page()
        page.goto(f"{live_server}/create/artist", wait_until="networkidle")
        page.get_by_role("button", name="Add Another Link").click()
        page.locator(_LINKS).nth(0).fill("https://example.com/a")
        page.locator(_LINKS).nth(1).fill("https://example.com/b")
        assert_screenshot(
            page.locator('input[name="links"]').first.locator(
                "xpath=ancestor::div[contains(@class, 'mt-2')][1]"
            ),
            "links-editor-two-rows",
        )
