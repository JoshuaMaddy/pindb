"""Build a display in the editor, then share it.

Drives the ``display-editor`` island the way a user does — a real multi-file
pick, a real caption, a real pin tag through the select helpers — and then loads
the public page a logged-out visitor would land on from a shared link.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import expect

from tests.e2e.island_helpers import wait_for_islands
from tests.e2e.select_helpers import multi_add
from tests.helpers.binary_fixtures import tiny_png_bytes

# The island renders one <li> per photo; nothing else on the page is a ul > li.
_TILE = "ul > li"
_FILE_INPUT = "[data-testid='display-image-input']"
# Scoped: the app shell's nav carries its own form with a submit button.
_SETTINGS_FORM = "[data-testid='display-settings-form']"
# A display is 1:1 with a user, so each spec below owns its own account —
# otherwise they mutate the same row and the screenshots depend on test order.
_DISPLAY_OWNER = "e2e_admin_pw"
_LAYOUT_OWNER = "e2e_editor_pw"


def _open_editor(context, live_server):
    page = context.new_page()
    page.goto(f"{live_server}/user/me/display/edit")
    wait_for_islands(page)
    return page


def _pick_photos(page, count: int) -> None:
    """Upload *count* photos through the real (hidden, ``multiple``) file input."""
    page.locator(_FILE_INPUT).wait_for(state="attached")
    page.locator(_FILE_INPUT).set_input_files(
        [
            {
                "name": f"display-{index}.png",
                "mimeType": "image/png",
                "buffer": tiny_png_bytes(),
            }
            for index in range(count)
        ]
    )
    # Uploads are sequential, one request per photo.
    expect(page.locator(_TILE)).to_have_count(count, timeout=30_000)


@pytest.mark.slow
def test_build_a_display_and_share_it(
    admin_browser_context, live_server, make_pin, assert_screenshot
):
    pin = make_pin("DisplayTaggedPin")
    page = _open_editor(admin_browser_context, live_server)

    _pick_photos(page, 2)

    first_tile = page.locator(_TILE).first
    caption = first_tile.locator("input[aria-label='Caption']")
    caption.fill("The top shelf")
    caption.blur()  # commits without waiting out the debounce

    # Widen the first photo — the span-2 size hint the grid layout reads.
    first_tile.locator("button[title^='Wide']").click()
    expect(first_tile.locator("button[aria-pressed='true']")).to_be_visible()

    # Tag a pin. Through the helpers, never the widget internals.
    multi_add(page, first_tile.locator("select"), pin["name"])

    # The settings form is a real submit that redirects, so it goes last.
    settings = page.locator(_SETTINGS_FORM)
    settings.locator("input[name='title']").fill("My Shadow Box")
    settings.locator("textarea[name='blurb']").fill(
        "Everything I've collected this year."
    )
    # The response is an HX-Redirect, so the navigation starts *after* the POST
    # settles — waiting on "load" alone would race the reload and screenshot a
    # page that is already being torn down.
    with page.expect_navigation(wait_until="load"):
        settings.locator("button[type='submit']").click()
    wait_for_islands(page)

    # Everything the island saved as-you-go survived the round trip.
    expect(page.locator(_TILE)).to_have_count(2)
    expect(
        page.locator(_TILE).first.locator("input[aria-label='Caption']")
    ).to_have_value("The top shelf")
    assert_screenshot(page, "display-editor-two-photos")

    # What a visitor arriving from a shared link actually sees.
    anon = admin_browser_context.browser.new_context()
    try:
        public = anon.new_page()
        public.goto(f"{live_server}/user/{_DISPLAY_OWNER}/display")
        public.wait_for_load_state("load")

        expect(public.locator("h1")).to_contain_text("My Shadow Box")
        expect(public.locator("body")).to_contain_text("The top shelf")
        expect(public.locator("body")).to_contain_text("DisplayTaggedPin")
        expect(public.locator("figure img")).to_have_count(2)

        # The share card is the whole point of the feature.
        expect(public.locator("meta[property='og:image']")).to_have_attribute(
            "content", re.compile(r"/get/og-image/user_display/\d+$")
        )
        assert_screenshot(public, "display-page-default")
    finally:
        anon.close()


@pytest.mark.slow
def test_each_layout_renders(editor_browser_context, live_server, assert_screenshot):
    """The span-2 feature hint is the thing most likely to silently regress.

    Runs as the *editor*, not the admin: a display is 1:1 with a user, so sharing
    one account with the test above would make both specs mutate the same row and
    leave each other's photo count to chance — the screenshots would then differ
    by test order rather than by layout.
    """
    page = _open_editor(editor_browser_context, live_server)
    _pick_photos(page, 3)
    first_tile = page.locator(_TILE).first
    first_tile.locator("button[title^='Wide']").click()
    expect(first_tile.locator("button[aria-pressed='true']")).to_be_visible()

    for layout in ("Grid", "Vertical"):
        page.locator(f"button:has-text('{layout}')").click()
        public = editor_browser_context.new_page()
        public.goto(f"{live_server}/user/{_LAYOUT_OWNER}/display")
        public.wait_for_load_state("load")
        expect(public.locator("figure img")).to_have_count(3)
        assert_screenshot(public, f"display-page-{layout.lower()}")
        public.close()
