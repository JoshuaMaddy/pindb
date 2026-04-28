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
from typing import TYPE_CHECKING, Any

import httpx
import pytest
from playwright.sync_api import expect

if TYPE_CHECKING:
    from collections.abc import Callable

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


def _create_tag_with_implications(
    client: httpx.Client,
    db_handle,
    *,
    name: str,
    implication_ids: tuple[int, ...] = (),
    category: str = "general",
) -> int:
    """Create a tag via HTTP and return its id (``name`` is stored normalized)."""
    payload: dict[str, Any] = {"name": name, "category": category}
    if implication_ids:
        payload["implication_ids"] = [str(i) for i in implication_ids]
    response = client.post(
        "/create/tag",
        data=payload,
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200, response.text[:400]
    rows = db_handle(
        "SELECT id FROM tags WHERE name = %s",
        (name,),
    )
    assert rows, f"tag {name!r} missing after create"
    return int(rows[0][0])


def _create_pin_set_http(client: httpx.Client, db_handle, *, name: str) -> int:
    response = client.post(
        "/create/pin_set",
        data={"name": name, "description": "e2e pin set"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200, response.text[:400]
    rows = db_handle("SELECT id FROM pin_sets WHERE name = %s", (name,))
    assert rows, f"pin_set {name!r} missing after create"
    return int(rows[0][0])


def _build_implication_chain_length_five(
    client: httpx.Client,
    db_handle,
    prefix: str,
) -> tuple[int, tuple[str, ...]]:
    """Build ``prefix_a`` → … → ``prefix_e`` (each implies the next). Return head id + five tag names."""
    e_id = _create_tag_with_implications(client, db_handle, name=f"{prefix}_e")
    d_id = _create_tag_with_implications(
        client, db_handle, name=f"{prefix}_d", implication_ids=(e_id,)
    )
    c_id = _create_tag_with_implications(
        client, db_handle, name=f"{prefix}_c", implication_ids=(d_id,)
    )
    b_id = _create_tag_with_implications(
        client, db_handle, name=f"{prefix}_b", implication_ids=(c_id,)
    )
    a_id = _create_tag_with_implications(
        client, db_handle, name=f"{prefix}_a", implication_ids=(b_id,)
    )
    names = tuple(f"{prefix}_{letter}" for letter in ("a", "b", "c", "d", "e"))
    return a_id, names


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

    def test_anonymous_create_pin_is_forbidden(self, anon_http_client):
        response = anon_http_client.get("/create/pin")
        assert response.status_code in (401, 403)


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


# ---------------------------------------------------------------------------
# Exhaustive field coverage (HTTP multipart; validates persistence end-to-end)
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestFullPinFieldCoverage:
    def test_create_pin_with_all_fields(
        self,
        admin_http_client,
        db_handle,
        make_shop,
        make_artist,
        make_pin,
        make_tag,
    ):
        from pindb.model_utils import magnitude_to_mm

        prefix = "e2efull"
        pin_name = "E2e Full Field Pin"

        shop_a = make_shop(f"{prefix}_shop_a", approved=True)
        shop_b = make_shop(f"{prefix}_shop_b", approved=True)
        artist_a = make_artist(f"{prefix}_artist_a", approved=True)
        artist_b = make_artist(f"{prefix}_artist_b", approved=True)

        set_a = _create_pin_set_http(
            admin_http_client, db_handle, name=f"{prefix}_set_a"
        )
        set_b = _create_pin_set_http(
            admin_http_client, db_handle, name=f"{prefix}_set_b"
        )

        chain_head_id, chain_tag_names = _build_implication_chain_length_five(
            admin_http_client, db_handle, f"{prefix}_cascade"
        )
        tag_x1 = make_tag(f"{prefix}_extra_one", approved=True)
        tag_x2 = make_tag(f"{prefix}_extra_two", approved=True)

        variant_a = make_pin(f"{prefix}_variant_seed_a", approved=True)
        variant_b = make_pin(f"{prefix}_variant_seed_b", approved=True)
        copy_a = make_pin(f"{prefix}_copy_seed_a", approved=True)
        copy_b = make_pin(f"{prefix}_copy_seed_b", approved=True)

        cur_rows = db_handle("SELECT id FROM currencies WHERE code = 'USD' LIMIT 1")
        assert cur_rows
        currency_id = int(cur_rows[0][0])

        files = {
            "front_image": (
                "front.png",
                io.BytesIO(_png_bytes(width=2, height=2)),
                "image/png",
            ),
            "back_image": (
                "back.png",
                io.BytesIO(_png_bytes(width=2, height=2)),
                "image/png",
            ),
        }
        data: dict[str, Any] = {
            "name": pin_name,
            "description": "## Complete pin\n\nDescription **body**.",
            "acquisition_type": "blind_box",
            "grade_names": ["collector", "standard"],
            "grade_prices": ["24.99", "12.00"],
            "currency_id": str(currency_id),
            "shop_ids": [str(shop_a["id"]), str(shop_b["id"])],
            "tag_ids": [str(chain_head_id), str(tag_x1["id"]), str(tag_x2["id"])],
            "pin_sets_ids": [str(set_a), str(set_b)],
            "artist_ids": [str(artist_a["id"]), str(artist_b["id"])],
            "variant_pin_ids": [str(variant_a["id"]), str(variant_b["id"])],
            "unauthorized_copy_pin_ids": [str(copy_a["id"]), str(copy_b["id"])],
            "limited_edition": "true",
            "number_produced": "750",
            "release_date": "2023-06-01",
            "end_date": "2028-01-15",
            "funding_type": "sponsored",
            "posts": "2",
            "width": "45mm",
            "height": "1.5in",
            "links": [
                "https://example.com/full-pin-primary",
                "https://example.org/full-pin-secondary",
            ],
        }

        response = admin_http_client.post("/create/pin", data=data, files=files)
        assert response.status_code == 200, response.text[:600]
        assert response.headers.get("hx-redirect"), response.headers

        prow = db_handle(
            "SELECT id, acquisition_type, limited_edition, number_produced, "
            "funding_type, posts, width, height, description, currency_id, "
            "release_date, end_date, back_image_guid IS NOT NULL "
            "FROM pins WHERE name = %s",
            (pin_name,),
        )
        assert prow
        (
            pid,
            acquisition_type,
            limited_edition,
            number_produced,
            funding_type,
            posts,
            width_mm,
            height_mm,
            description,
            pin_currency_id,
            release_date,
            end_date,
            has_back,
        ) = prow[0]

        assert acquisition_type == "blind_box"
        assert limited_edition is True
        assert number_produced == 750
        assert funding_type == "sponsored"
        assert posts == 2
        assert width_mm == pytest.approx(magnitude_to_mm("45mm"))
        assert height_mm == pytest.approx(magnitude_to_mm("1.5in"))
        assert description == "## Complete pin\n\nDescription **body**."
        assert pin_currency_id == currency_id
        assert str(release_date) == "2023-06-01"
        assert str(end_date) == "2028-01-15"
        assert has_back is True

        assert (
            db_handle(
                "SELECT COUNT(*) FROM pins_shops WHERE pin_id = %s",
                (pid,),
            )[0][0]
            == 2
        )
        assert (
            db_handle(
                "SELECT COUNT(*) FROM pins_artists WHERE pin_id = %s",
                (pid,),
            )[0][0]
            == 2
        )
        assert (
            db_handle(
                "SELECT COUNT(*) FROM pin_set_memberships WHERE pin_id = %s",
                (pid,),
            )[0][0]
            == 2
        )

        grade_rows = db_handle(
            "SELECT g.name, g.price FROM pins_grades pg "
            "JOIN grades g ON pg.grade_id = g.id WHERE pg.pin_id = %s ORDER BY g.name",
            (pid,),
        )
        assert grade_rows == [
            ("collector", pytest.approx(24.99)),
            ("standard", pytest.approx(12.00)),
        ]

        link_rows = db_handle(
            "SELECT l.path FROM pins_links pl JOIN links l ON pl.link_id = l.id "
            "WHERE pl.pin_id = %s ORDER BY l.path",
            (pid,),
        )
        assert [row[0] for row in link_rows] == [
            "https://example.com/full-pin-primary",
            "https://example.org/full-pin-secondary",
        ]

        assert (
            db_handle(
                "SELECT COUNT(*) FROM pin_variants WHERE pin_id = %s",
                (pid,),
            )[0][0]
            == 2
        )
        assert (
            db_handle(
                "SELECT COUNT(*) FROM pin_unauthorized_copies WHERE pin_id = %s",
                (pid,),
            )[0][0]
            == 2
        )

        explicit_count = db_handle(
            "SELECT COUNT(*) FROM pins_tags WHERE pin_id = %s AND implied_by_tag_id IS NULL",
            (pid,),
        )[0][0]
        assert explicit_count == 3

        implied_count = db_handle(
            "SELECT COUNT(*) FROM pins_tags WHERE pin_id = %s AND implied_by_tag_id IS NOT NULL",
            (pid,),
        )[0][0]
        assert implied_count == 4

        chain_placeholders = ",".join(["%s"] * len(chain_tag_names))
        chain_present = db_handle(
            f"SELECT COUNT(DISTINCT t.name) FROM pins_tags pt "
            f"JOIN tags t ON pt.tag_id = t.id "
            f"WHERE pt.pin_id = %s AND t.name IN ({chain_placeholders})",
            (pid, *chain_tag_names),
        )[0][0]
        assert chain_present == 5
