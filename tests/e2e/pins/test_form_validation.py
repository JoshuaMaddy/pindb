"""Browser e2e for pin create/edit client-side validation (`pin_creation.js`)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.pins._helpers import png_bytes
from tests.e2e.select_helpers import (
    multi_add,
    single_pick,
    wait_for_option_indexed,
    widget_root,
)


def _browser(role: str, admin_browser_context, editor_browser_context):
    return admin_browser_context if role == "admin" else editor_browser_context


def _pin_form_options_url(page: Page, entity_type: str) -> str:
    """Options endpoint for a pin-form multi-select, read from the ref JSON."""
    base = page.evaluate(
        "() => JSON.parse(document.getElementById('pin-form-ref-data').textContent)"
        ".optionsBaseUrl"
    )
    return f"{base}/{entity_type}"


def _wait_for_grade_inputs_ready(page: Page) -> None:
    page.wait_for_function(
        """() => {
          const inputs = document.querySelectorAll(
            '#pin-form input[name="grade_names"]',
          );
          return inputs.length > 0 && [...inputs].some((i) => i.value.trim());
        }""",
        timeout=15000,
    )


@pytest.mark.slow
@pytest.mark.parametrize("role", ["editor", "admin"])
class TestPinFormClientValidation:
    def test_empty_submit_shows_inline_hints_and_keeps_submit_disabled(
        self,
        role,
        admin_browser_context,
        editor_browser_context,
        live_server,
    ):
        page = _browser(role, admin_browser_context, editor_browser_context).new_page()
        page.goto(f"{live_server}/create/pin")
        page.wait_for_load_state("load")
        _wait_for_grade_inputs_ready(page)

        submit = page.locator("#pin-form-submit")
        expect(submit).to_have_attribute("aria-disabled", "true")

        submit.click(force=True)

        hints = page.locator(".pin-form-field-hint")
        expect(hints).to_have_count(4)
        expect(
            page.get_by_text("Enter a name for this pin.", exact=True)
        ).to_be_visible()
        expect(page.get_by_text("Upload a front image.", exact=True)).to_be_visible()
        expect(submit).to_have_attribute("aria-disabled", "true")

    def test_name_hint_cleared_after_fill_without_resubmit(
        self,
        role,
        admin_browser_context,
        editor_browser_context,
        live_server,
    ):
        page = _browser(role, admin_browser_context, editor_browser_context).new_page()
        page.goto(f"{live_server}/create/pin")
        page.wait_for_load_state("load")
        _wait_for_grade_inputs_ready(page)

        page.locator("#pin-form-submit").click(force=True)
        expect(page.get_by_text("Enter a name for this pin.")).to_be_visible()

        page.fill("#name", "Filled Name Client Validation")
        expect(page.get_by_text("Enter a name for this pin.")).to_have_count(0)

    def test_submit_enables_when_required_fields_satisfied(
        self,
        role,
        admin_browser_context,
        editor_browser_context,
        live_server,
        make_shop,
        make_tag,
    ):
        shop = make_shop("ValSubmitShop", approved=True)
        tag = make_tag("val_submit_tag", approved=True)

        page = _browser(role, admin_browser_context, editor_browser_context).new_page()
        page.goto(f"{live_server}/create/pin")
        page.wait_for_load_state("load")
        _wait_for_grade_inputs_ready(page)

        submit = page.locator("#pin-form-submit")
        expect(submit).to_have_attribute("aria-disabled", "true")

        page.fill("#name", "Client Validation Ready Pin")

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(png_bytes())
            tmp_path = tmp.name
        try:
            page.set_input_files("#front_image", tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        # UI-driven picks: remote-loading selects need the entities indexed.
        wait_for_option_indexed(
            page, _pin_form_options_url(page, "shop"), "ValSubmitShop"
        )
        wait_for_option_indexed(
            page, _pin_form_options_url(page, "tag"), "val_submit_tag"
        )
        # Underscore names: query the first name chunk (the search backend
        # doesn't split on underscores) and match the rendered display text.
        multi_add(page, page.locator("#shop_ids"), "ValSubmitShop")
        multi_add(page, page.locator("#tag_ids"), "val", option_text="val submit tag")
        single_pick(page, page.locator("#acquisition_type"), "Single")

        expect(submit).to_have_attribute("aria-disabled", "false")


@pytest.mark.slow
def test_tag_chip_visual_baseline(
    admin_browser_context, live_server, make_tag, assert_screenshot
):
    """Selected tag renders as a category-colored chip in the widget control."""
    tag = make_tag("chip_visual_tag", approved=True)
    page = admin_browser_context.new_page()
    page.goto(f"{live_server}/create/pin", wait_until="networkidle")

    wait_for_option_indexed(page, _pin_form_options_url(page, "tag"), tag["name"])
    multi_add(page, page.locator("#tag_ids"), "chip", option_text="chip visual tag")
    assert_screenshot(widget_root(page.locator("#tag_ids")), "pin-form-tag-chips")
