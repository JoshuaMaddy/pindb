"""E2e coverage for create flows: shop, artist, tag, pin set — editor + admin.

Includes client-side gate UX (entity_form_gate.js), successful creates, server
failure (duplicate name), and auth failure for non-editors.
"""

from __future__ import annotations

import uuid

import pytest
from playwright.sync_api import expect

from pindb.database.tag import normalize_tag_name


def _browser(role: str, admin_browser_context, editor_browser_context):
    return admin_browser_context if role == "admin" else editor_browser_context


@pytest.mark.slow
@pytest.mark.parametrize("role", ["editor", "admin"])
class TestEntityFormClientValidation:
    def test_shop_empty_submit_shows_hint(
        self,
        role,
        admin_browser_context,
        editor_browser_context,
        live_server,
    ):
        page = _browser(role, admin_browser_context, editor_browser_context).new_page()
        page.goto(f"{live_server}/create/shop")
        page.wait_for_load_state("load")

        submit = page.locator("#simple-entity-submit")
        expect(submit).to_have_attribute("aria-disabled", "true")
        submit.click(force=True)

        expect(page.locator(".entity-form-field-hint")).to_have_count(1)
        expect(page.get_by_text("Enter a shop name.", exact=True)).to_be_visible()

    def test_artist_empty_submit_shows_hint(
        self,
        role,
        admin_browser_context,
        editor_browser_context,
        live_server,
    ):
        page = _browser(role, admin_browser_context, editor_browser_context).new_page()
        page.goto(f"{live_server}/create/artist")
        page.wait_for_load_state("load")

        page.locator("#simple-entity-submit").click(force=True)
        expect(page.get_by_text("Enter an artist name.", exact=True)).to_be_visible()

    def test_tag_empty_submit_shows_hint(
        self,
        role,
        admin_browser_context,
        editor_browser_context,
        live_server,
    ):
        page = _browser(role, admin_browser_context, editor_browser_context).new_page()
        page.goto(f"{live_server}/create/tag")
        page.wait_for_load_state("load")

        page.locator("#tag-form-submit").click(force=True)
        expect(page.get_by_text("Enter a tag name.", exact=True)).to_be_visible()

    def test_pin_set_empty_submit_shows_hint(
        self,
        role,
        admin_browser_context,
        editor_browser_context,
        live_server,
    ):
        page = _browser(role, admin_browser_context, editor_browser_context).new_page()
        page.goto(f"{live_server}/create/pin_set")
        page.wait_for_load_state("load")

        page.locator("#pin-set-create-submit").click(force=True)
        expect(
            page.get_by_text("Enter a name for this pin set.", exact=True)
        ).to_be_visible()


@pytest.mark.slow
@pytest.mark.parametrize("role", ["editor", "admin"])
class TestEntityCreateSuccess:
    def test_shop_create_submits(
        self,
        role,
        admin_browser_context,
        editor_browser_context,
        live_server,
        db_handle,
    ):
        suffix = uuid.uuid4().hex[:10]
        name = f"E2e Shop {role} {suffix}"

        page = _browser(role, admin_browser_context, editor_browser_context).new_page()
        page.goto(f"{live_server}/create/shop")
        page.wait_for_load_state("load")

        page.fill("#name", name)

        with page.expect_response(
            lambda r: (
                r.url.rstrip("/").endswith("/create/shop")
                and r.request.method == "POST"
            ),
            timeout=30_000,
        ) as resp_info:
            page.locator("#simple-entity-submit").click()
        resp = resp_info.value
        assert resp.ok
        assert resp.headers.get("hx-redirect")

        rows = db_handle("SELECT id FROM shops WHERE name = %s", (name,))
        assert rows

    def test_artist_create_submits(
        self,
        role,
        admin_browser_context,
        editor_browser_context,
        live_server,
        db_handle,
    ):
        suffix = uuid.uuid4().hex[:10]
        name = f"E2e Artist {role} {suffix}"

        page = _browser(role, admin_browser_context, editor_browser_context).new_page()
        page.goto(f"{live_server}/create/artist")
        page.wait_for_load_state("load")

        page.fill("#name", name)

        with page.expect_response(
            lambda r: "/create/artist" in r.url and r.request.method == "POST",
            timeout=30_000,
        ) as resp_info:
            page.locator("#simple-entity-submit").click()
        assert resp_info.value.ok
        assert resp_info.value.headers.get("hx-redirect")

        rows = db_handle("SELECT id FROM artists WHERE name = %s", (name,))
        assert rows

    def test_tag_create_submits(
        self,
        role,
        admin_browser_context,
        editor_browser_context,
        live_server,
        db_handle,
    ):
        suffix = uuid.uuid4().hex[:10]
        raw_name = f"e2e_tag_{role}_{suffix}"
        filled = raw_name.replace("_", " ")

        page = _browser(role, admin_browser_context, editor_browser_context).new_page()
        page.goto(f"{live_server}/create/tag")
        page.wait_for_load_state("load")

        page.fill("#name", filled)

        with page.expect_response(
            lambda r: "/create/tag" in r.url and r.request.method == "POST",
            timeout=30_000,
        ) as resp_info:
            page.locator("#tag-form-submit").click()
        assert resp_info.value.ok
        assert resp_info.value.headers.get("hx-redirect")

        rows = db_handle(
            "SELECT id FROM tags WHERE name = %s",
            (normalize_tag_name(filled),),
        )
        assert rows

    def test_pin_set_create_submits(
        self,
        role,
        admin_browser_context,
        editor_browser_context,
        live_server,
        db_handle,
    ):
        suffix = uuid.uuid4().hex[:10]
        name = f"E2e PinSet {role} {suffix}"

        page = _browser(role, admin_browser_context, editor_browser_context).new_page()
        page.goto(f"{live_server}/create/pin_set")
        page.wait_for_load_state("load")

        page.fill("#name", name)

        with page.expect_response(
            lambda r: "/create/pin_set" in r.url and r.request.method == "POST",
            timeout=30_000,
        ) as resp_info:
            page.locator("#pin-set-create-submit").click()
        assert resp_info.value.ok
        assert resp_info.value.headers.get("hx-redirect")

        rows = db_handle("SELECT id FROM pin_sets WHERE name = %s", (name,))
        assert rows


@pytest.mark.slow
@pytest.mark.parametrize("role", ["editor", "admin"])
class TestEntityCreateFailureCases:
    def test_duplicate_shop_name_returns_error_toast_fragment(
        self,
        role,
        admin_browser_context,
        editor_browser_context,
        live_server,
        make_shop,
    ):
        dup_name = f"DupShop{uuid.uuid4().hex[:8]}"
        make_shop(dup_name, approved=True)

        page = _browser(role, admin_browser_context, editor_browser_context).new_page()
        page.goto(f"{live_server}/create/shop")
        page.wait_for_load_state("load")

        page.fill("#name", dup_name)

        with page.expect_response(
            lambda r: "/create/shop" in r.url and r.request.method == "POST",
            timeout=30_000,
        ) as resp_info:
            page.locator("#simple-entity-submit").click()
        resp = resp_info.value
        assert resp.ok
        body = resp.text()
        assert "pindb-toast-signal" in body
        assert 'data-pindb-type="error"' in body


@pytest.mark.slow
class TestEntityAuthGuard:
    def test_regular_user_get_create_shop_forbidden(
        self,
        regular_user_browser_context,
        live_server,
    ):
        page = regular_user_browser_context.new_page()
        resp = page.goto(f"{live_server}/create/shop")
        assert resp is not None
        assert resp.status == 403
