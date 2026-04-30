"""Reusable payload builders for pin route integration tests."""

from __future__ import annotations


def pin_form_data(
    *,
    name: str,
    acquisition_type: str = "single",
    currency_id: str = "999",
    shop_ids: list[int] | None = None,
    tag_ids: list[int] | None = None,
    artist_ids: list[int] | None = None,
    pin_sets_ids: list[int] | None = None,
    variant_pin_ids: list[int] | None = None,
    unauthorized_copy_pin_ids: list[int] | None = None,
) -> dict[str, str | list[str]]:
    return {
        "name": name,
        "acquisition_type": acquisition_type,
        "grade_names": ["Standard"],
        "grade_prices": ["12.50"],
        "currency_id": currency_id,
        "posts": "2",
        "description": "integration test pin",
        "width": "40mm",
        "height": "1.5in",
        "limited_edition": "true",
        "number_produced": "150",
        "funding_type": "self",
        "links": ["https://example.com/a", "https://example.com/b"],
        "shop_ids": [str(shop_id) for shop_id in (shop_ids or [])],
        "tag_ids": [str(tag_id) for tag_id in (tag_ids or [])],
        "artist_ids": [str(artist_id) for artist_id in (artist_ids or [])],
        "pin_sets_ids": [str(pin_set_id) for pin_set_id in (pin_sets_ids or [])],
        "variant_pin_ids": [
            str(variant_pin_id) for variant_pin_id in (variant_pin_ids or [])
        ],
        "unauthorized_copy_pin_ids": [
            str(copy_pin_id) for copy_pin_id in (unauthorized_copy_pin_ids or [])
        ],
    }
