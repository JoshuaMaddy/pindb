"""Pin image upload, retrieval, and thumbnail generation."""

from __future__ import annotations

import pytest

from tests.e2e.pins._helpers import admin_login_http, create_pin_via_http


@pytest.mark.slow
class TestPinImageRoundTrip:
    def test_uploaded_pin_image_is_retrievable_with_thumbnail(
        self,
        live_server,
        db_handle,
        make_shop,
    ):
        shop = make_shop("PinShop", approved=True)
        client = admin_login_http(live_server)
        try:
            response = create_pin_via_http(
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

            full = client.get(f"/get/image/{front_guid}")
            assert full.status_code == 200
            assert full.headers["content-type"].startswith("image")
            assert len(full.content) > 0

            thumb = client.get(f"/get/image/{front_guid}", params={"thumbnail": "true"})
            assert thumb.status_code == 200
            assert thumb.headers["content-type"].startswith("image/webp")
            assert len(thumb.content) > 0
        finally:
            client.close()

    def test_missing_image_guid_returns_404_not_null(self, live_server):
        client = admin_login_http(live_server)
        try:
            response = client.get("/get/image/00000000-0000-0000-0000-000000000000")
            assert response.status_code == 404
        finally:
            client.close()
