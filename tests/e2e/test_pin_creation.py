"""Pin creation flows.

The pin form is the most complex create surface in PinDB — it bundles a
file upload, a TomSelect-driven set of FK pickers, an Alpine x-data
grade-row table, and currency selection. We split the testing strategy:

  * **Image upload + storage round-trip**: drive the form via HTTP (faster,
    deterministic) using `multipart/form-data`, then verify `/get/image/{guid}`
    returns the bytes back AND that an on-demand thumbnail is generated.
  * **Cascade approval**: editor creates a pin referencing pending shop +
    pending artist; admin approves the pin; both deps cascade to approved
    in a single transaction.
  * **Browser-level smoke**: confirm the create-pin page renders for
    editor and that the file inputs are wired with the expected MIME
    `accept` attribute.

The intricate Alpine `x-data` grade-row UI is left to integration-level
tests (which are far cheaper).
"""

from __future__ import annotations

import io
import struct
import zlib
from typing import TYPE_CHECKING

import httpx
import pytest
from playwright.sync_api import expect

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _png_bytes(width: int = 1, height: int = 1) -> bytes:
    """A real, valid PNG (1×1 black pixel by default).

    Not a placeholder string — Pillow has to be able to open it for the
    thumbnail pipeline to succeed.
    """
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(typ: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + typ
            + data
            + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + b"\x00\x00\x00" * width for _ in range(height))
    idat = zlib.compress(raw)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def _admin_login(live_server: str) -> httpx.Client:
    client = httpx.Client(base_url=live_server, follow_redirects=False)
    client.post(
        "/auth/login",
        data={"username": "e2e_admin_pw", "password": "E2e-Admin-Secret-9!"},
    )
    return client


def _editor_login(live_server: str) -> httpx.Client:
    client = httpx.Client(base_url=live_server, follow_redirects=False)
    client.post(
        "/auth/login",
        data={"username": "e2e_editor_pw", "password": "E2e-Editor-Secret-9!"},
    )
    return client


def _create_pin_via_http(
    client: httpx.Client,
    *,
    name: str,
    shop_ids: list[int] | None = None,
    artist_ids: list[int] | None = None,
    tag_ids: list[int] | None = None,
) -> httpx.Response:
    files = {
        "front_image": ("front.png", io.BytesIO(_png_bytes()), "image/png"),
    }
    data: dict[str, str | list[str]] = {
        "name": name,
        "acquisition_type": "single",
        "grade_names": "standard",
        "grade_prices": "",
        "currency_id": "999",
        "posts": "1",
    }
    if shop_ids:
        data["shop_ids"] = [str(s) for s in shop_ids]
    if artist_ids:
        data["artist_ids"] = [str(a) for a in artist_ids]
    if tag_ids:
        data["tag_ids"] = [str(t) for t in tag_ids]
    return client.post("/create/pin", data=data, files=files)


# ---------------------------------------------------------------------------
# Image upload round-trip
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestPinImageRoundTrip:
    def test_uploaded_pin_image_is_retrievable_with_thumbnail(
        self,
        live_server,
        db_handle,
        make_shop,
    ):
        shop = make_shop("PinShop", approved=True)
        client = _admin_login(live_server)
        try:
            response = _create_pin_via_http(
                client,
                name="ImagePin",
                shop_ids=[int(shop["id"])],
            )
            assert response.status_code == 200, response.text[:500]
            assert response.headers.get("hx-redirect"), (
                "expected HX-Redirect to the new pin page"
            )

            rows = db_handle(
                "SELECT id, front_image_guid FROM pins WHERE name = 'ImagePin'"
            )
            assert rows, "pin row missing after create"
            _, front_guid = rows[0]
            assert front_guid is not None

            # Round-trip GET — full-size image.
            full = client.get(f"/get/image/{front_guid}")
            assert full.status_code == 200
            assert full.headers["content-type"].startswith("image")
            assert len(full.content) > 0

            # Thumbnail must be generated on demand and returned.
            thumb = client.get(f"/get/image/{front_guid}", params={"thumbnail": "true"})
            assert thumb.status_code == 200
            assert thumb.headers["content-type"].startswith("image/webp")
            assert len(thumb.content) > 0
        finally:
            client.close()

    def test_missing_image_guid_returns_404_not_null(self, live_server):
        client = _admin_login(live_server)
        try:
            response = client.get("/get/image/00000000-0000-0000-0000-000000000000")
            assert response.status_code == 404
        finally:
            client.close()


# ---------------------------------------------------------------------------
# Cascade approval on pin
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestPinCascadeApproval:
    def test_approving_pin_cascades_pending_shop_and_artist(
        self,
        admin_browser_context,
        live_server,
        db_handle,
        make_shop,
        make_artist,
    ):
        # Editor creates a pending shop + artist, then a pin referencing
        # both. Approving the pin should also approve the shop + artist.
        shop = make_shop("CascadeShop", approved=False)
        artist = make_artist("CascadeArtist", approved=False)

        client = _editor_login(live_server)
        try:
            response = _create_pin_via_http(
                client,
                name="CascadePin",
                shop_ids=[int(shop["id"])],
                artist_ids=[int(artist["id"])],
            )
            assert response.status_code == 200, response.text[:500]
        finally:
            client.close()

        # Pin is created in pending state; deps still pending.
        pin_rows = db_handle(
            "SELECT id, approved_at FROM pins WHERE name = 'CascadePin'"
        )
        assert pin_rows and pin_rows[0][1] is None

        # Admin approves the pin.
        admin_page = admin_browser_context.new_page()
        admin_page.goto(f"{live_server}/admin/pending")
        admin_page.wait_for_load_state("load")
        # The pin row's approve button — there's also a "Will also approve:"
        # hint we check is visible.
        pin_row = admin_page.locator("tr", has_text="CascadePin")
        expect(pin_row).to_contain_text("Will also approve")
        pin_row.locator("form[action*='/admin/pending/approve/pin/']").locator(
            "button[type='submit']"
        ).click()
        admin_page.wait_for_load_state("load")

        # Pin + shop + artist all approved in one shot.
        pin_rows = db_handle("SELECT approved_at FROM pins WHERE name = 'CascadePin'")
        shop_rows = db_handle(
            "SELECT approved_at FROM shops WHERE name = 'CascadeShop'"
        )
        artist_rows = db_handle(
            "SELECT approved_at FROM artists WHERE name = 'CascadeArtist'"
        )
        assert pin_rows[0][0] is not None, "pin not approved"
        assert shop_rows[0][0] is not None, "shop not cascaded"
        assert artist_rows[0][0] is not None, "artist not cascaded"


# ---------------------------------------------------------------------------
# UI smoke checks on the create-pin page
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestCreatePinFormSurface:
    def test_create_pin_page_renders_for_editor(
        self, editor_browser_context, live_server
    ):
        page = editor_browser_context.new_page()
        page.goto(f"{live_server}/create/pin")
        page.wait_for_load_state("load")
        # Required name input is present.
        expect(page.locator("input[name='name']")).to_be_visible()
        # File inputs are present (visually hidden by `class_="hidden"`).
        expect(page.locator("input[name='front_image']")).to_have_attribute(
            "accept", "image/png, image/jpeg, image/jpg, image/webp"
        )
        expect(page.locator("input[name='back_image']")).to_have_attribute(
            "accept", "image/png, image/jpeg, image/jpg, image/webp"
        )

    def test_anonymous_create_pin_is_forbidden(self, anon_browser_context, live_server):
        page = anon_browser_context.new_page()
        response = page.goto(f"{live_server}/create/pin")
        assert response is not None
        assert response.status in (401, 403)


# ---------------------------------------------------------------------------
# Editor's pin shows up in pending queue with "Will also approve" hint
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestPendingQueueCascadeHint:
    def test_will_also_approve_lists_pending_dependencies(
        self,
        admin_browser_context,
        live_server,
        make_shop: Callable[..., dict[str, Any]],
    ):
        pending_shop = make_shop("HintShop", approved=False)

        client = _editor_login(live_server)
        try:
            response = _create_pin_via_http(
                client,
                name="HintPin",
                shop_ids=[int(pending_shop["id"])],
            )
            assert response.status_code == 200, response.text[:500]
        finally:
            client.close()

        admin_page = admin_browser_context.new_page()
        admin_page.goto(f"{live_server}/admin/pending")
        admin_page.wait_for_load_state("load")
        pin_row = admin_page.locator("tr", has_text="HintPin")
        expect(pin_row).to_contain_text("Will also approve: HintShop")
