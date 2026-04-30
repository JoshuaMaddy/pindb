"""Browser e2e for pin create/edit client-side validation (`pin_creation.js`)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.pins._helpers import png_bytes


def _browser(role: str, admin_browser_context, editor_browser_context):
    return admin_browser_context if role == "admin" else editor_browser_context


def _set_tomselect_values(page: Page, select_id: str, values: list[str]) -> None:
    page.evaluate(
        """([sid, vals]) => {
            const el = document.getElementById(sid);
            if (!el || !el.tomselect) throw new Error('no tomselect for ' + sid);
            const ts = el.tomselect;
            if (el.multiple) {
              vals.forEach((raw) => {
                const v = String(raw);
                if (!ts.options[v]) {
                  ts.addOption({ value: v, text: v });
                }
              });
              ts.setValue(vals.map(String), true);
            } else {
              ts.setValue(vals[0], true);
            }
        }""",
        [select_id, values],
    )


def _pin_form_dispatch_refresh(page: Page) -> None:
    page.evaluate(
        """() => {
          const f = document.getElementById('pin-form');
          if (!f) return;
          f.dispatchEvent(new Event('input', { bubbles: true }));
          f.dispatchEvent(new Event('change', { bubbles: true }));
        }"""
    )


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

        _set_tomselect_values(page, "shop_ids", [str(shop["id"])])
        _set_tomselect_values(page, "tag_ids", [str(tag["id"])])
        _set_tomselect_values(page, "acquisition_type", ["single"])
        _pin_form_dispatch_refresh(page)

        expect(submit).to_have_attribute("aria-disabled", "false")
