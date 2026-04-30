"""Exhaustive multipart pin create (HTTP)."""

from __future__ import annotations

import io
from typing import Any

import pytest

from tests.e2e.pins._helpers import (
    build_implication_chain_length_five,
    create_pin_set_http,
    png_bytes,
)


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

        set_a = create_pin_set_http(
            admin_http_client, db_handle, name=f"{prefix}_set_a"
        )
        set_b = create_pin_set_http(
            admin_http_client, db_handle, name=f"{prefix}_set_b"
        )

        chain_head_id, chain_tag_names = build_implication_chain_length_five(
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
                io.BytesIO(png_bytes(width=2, height=2)),
                "image/png",
            ),
            "back_image": (
                "back.png",
                io.BytesIO(png_bytes(width=2, height=2)),
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
