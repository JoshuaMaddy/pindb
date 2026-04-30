"""404 behaviour for missing assets and entities."""

from __future__ import annotations


class TestNotFound:
    def test_missing_image_returns_404(self, admin_http_client):
        response = admin_http_client.get(
            "/get/image/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    def test_edit_missing_shop_returns_404(self, admin_http_client):
        response = admin_http_client.get("/edit/shop/9999999")
        assert response.status_code == 404
