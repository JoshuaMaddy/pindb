"""Pin form image upload: behavior contract for the vanilla → island port.

Written against the legacy ``pins/pin_creation.js`` implementation first
(lockstep protocol); must pass unchanged after the ``pin-images`` island port.
Stable contract: ``#front_image_preview`` / ``#back_image_preview`` boxes,
hidden ``#front_image`` / ``#back_image`` file inputs, client-side WebP
transcode before submit.
"""

from __future__ import annotations

import io

from playwright.sync_api import expect

from tests.e2e.select_helpers import (
    multi_add,
    single_pick,
    wait_for_option_indexed,
)
from tests.helpers.binary_fixtures import tiny_png_bytes


def _png_payload() -> dict[str, str | bytes]:
    return {
        "name": "front.png",
        "mimeType": "image/png",
        "buffer": tiny_png_bytes(),
    }


def _goto_pin_form(page, url: str) -> None:
    """Open a pin form and wait for the ``pin-images`` island to have mounted.

    Not ``wait_until="networkidle"``: that waits for 500ms of silent network on a
    page that pulls in islands, lucide and the webp encoder, and the context's
    navigation timeout is 5s — under CI load it is a coin flip, and it flaked
    exactly that way. The preview boxes are rendered by the island itself, so
    waiting on one is both deterministic and the thing these tests actually need.
    """
    page.goto(url, wait_until="load")
    page.locator("#front_image_preview").wait_for(state="visible")


def _fill_required_non_image_fields(page, shop_name: str, tag_name: str) -> None:
    """Satisfy the client gate through the select widget UI."""
    page.locator("#name").fill("ImageIslandPin")
    options_base = page.evaluate(
        "() => JSON.parse(document.getElementById('pin-form-ref-data').textContent)"
        ".optionsBaseUrl"
    )
    # Multi-selects are remote-loading (zero server-rendered options); wait
    # for the fixtures to land in the search index before typing.
    wait_for_option_indexed(page, f"{options_base}/shop", shop_name)
    wait_for_option_indexed(page, f"{options_base}/tag", tag_name)
    multi_add(page, page.locator("#shop_ids"), shop_name)
    multi_add(page, page.locator("#tag_ids"), tag_name)
    single_pick(page, page.locator("#acquisition_type"), "Single")


class TestPinImageUpload:
    def test_picker_upload_preview_then_webp_submit(
        self, admin_browser_context, live_server, make_shop, make_tag, db_handle
    ):
        shop = make_shop("ImgShop")
        tag = make_tag("img-tag")
        page = admin_browser_context.new_page()
        _goto_pin_form(page, f"{live_server}/create/pin")

        page.locator("#front_image").set_input_files([_png_payload()])
        # Preview renders a data URL after the (async) webp transcode.
        page.wait_for_function(
            "document.getElementById('front_image_preview').style.backgroundImage.includes('url(')",
            timeout=10_000,
        )

        # Client-side transcode replaced the picked PNG with a WebP file — the
        # form submit carries input.files, so this is what the server receives.
        # (Playwright does not expose multipart XHR bodies, so assert here.)
        file_meta = page.evaluate(
            "() => { const f = document.getElementById('front_image').files[0];"
            " return { type: f.type, name: f.name }; }"
        )
        assert file_meta["type"] == "image/webp", file_meta

        _fill_required_non_image_fields(page, shop["name"], tag["name"])
        expect(page.locator("#pin-form-submit")).to_be_enabled()

        with page.expect_response(
            lambda r: r.request.method == "POST" and "/create/pin" in r.url
        ) as response_info:
            page.locator("#pin-form-submit").click()
        assert response_info.value.status < 400

        rows = db_handle(
            "SELECT front_image_guid IS NOT NULL FROM pins WHERE name = %s",
            ("ImageIslandPin",),
        )
        assert rows and rows[0][0] is True

    def test_paste_upload_shows_back_preview(self, admin_browser_context, live_server):
        page = admin_browser_context.new_page()
        _goto_pin_form(page, f"{live_server}/create/pin")

        page.hover("#back_image_preview")
        png_b64 = io.BytesIO(tiny_png_bytes()).getvalue()
        page.evaluate(
            """(bytes) => {
                const file = new File(
                    [new Uint8Array(bytes)], 'pasted.png', { type: 'image/png' });
                const dt = new DataTransfer();
                dt.items.add(file);
                const evt = new ClipboardEvent('paste', {
                    clipboardData: dt, bubbles: true, cancelable: true });
                document.dispatchEvent(evt);
            }""",
            list(png_b64),
        )
        page.wait_for_function(
            "document.getElementById('back_image_preview').style.backgroundImage.includes('url(')",
            timeout=10_000,
        )
        files = page.evaluate("document.getElementById('back_image').files.length")
        assert files == 1

    def test_edit_replace_back_image_roundtrip(
        self, admin_browser_context, live_server, make_pin, db_handle
    ):
        pin = make_pin("BackImagePin", tag_names=["backimg-tag"])
        page = admin_browser_context.new_page()
        _goto_pin_form(page, f"{live_server}/edit/pin/{pin['id']}")

        page.locator("#back_image").set_input_files([_png_payload()])
        page.wait_for_function(
            "document.getElementById('back_image_preview').style.backgroundImage.includes('url(')",
            timeout=10_000,
        )

        with page.expect_response(
            lambda r: r.request.method == "POST" and f"/edit/pin/{pin['id']}" in r.url
        ) as response_info:
            page.locator("#pin-form-submit").click()
        assert response_info.value.status < 400

        rows = db_handle(
            "SELECT back_image_guid IS NOT NULL FROM pins WHERE id = %s",
            (pin["id"],),
        )
        assert rows and rows[0][0] is True

    def test_image_boxes_visual_baseline(
        self, admin_browser_context, live_server, assert_screenshot
    ):
        page = admin_browser_context.new_page()
        _goto_pin_form(page, f"{live_server}/create/pin")
        assert_screenshot(
            page.locator("#pin-form > div").first,
            "pin-images-empty",
        )
