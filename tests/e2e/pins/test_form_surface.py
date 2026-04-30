"""Browser smoke checks on the create-pin page."""

from __future__ import annotations

import pytest
from playwright.sync_api import expect


@pytest.mark.slow
class TestCreatePinFormSurface:
    def test_create_pin_page_renders_for_editor(
        self, editor_browser_context, live_server
    ):
        page = editor_browser_context.new_page()
        page.goto(f"{live_server}/create/pin")
        page.wait_for_load_state("load")
        expect(page.locator("input[name='name']")).to_be_visible()
        expect(page.locator("input[name='front_image']")).to_have_attribute(
            "accept", "image/png, image/jpeg, image/jpg, image/webp"
        )
        expect(page.locator("input[name='back_image']")).to_have_attribute(
            "accept", "image/png, image/jpeg, image/jpg, image/webp"
        )

    def test_anonymous_create_pin_is_forbidden(self, anon_http_client):
        response = anon_http_client.get("/create/pin")
        assert response.status_code in (401, 403)
