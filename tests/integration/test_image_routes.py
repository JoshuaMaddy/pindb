"""`/get/image/{guid}` with the filesystem backend (default in tests)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from pindb.http_caching import IMAGE_CACHE_CONTROL


@pytest.mark.integration
class TestImageRoute:
    def test_upload_then_fetch_roundtrip(self, admin_client, png_upload):
        """Upload a PNG via /bulk/pin/image, then fetch it by GUID."""
        upload = admin_client.post("/bulk/pin/image", files={"image": png_upload})
        guid = upload.json()["guid"]

        response = admin_client.get(f"/get/image/{guid}", follow_redirects=False)
        assert response.status_code == 200
        assert response.content  # non-empty bytes
        assert response.headers["cache-control"] == IMAGE_CACHE_CONTROL

    def test_thumbnail_generated_on_demand(self, admin_client, png_upload):
        upload = admin_client.post("/bulk/pin/image", files={"image": png_upload})
        guid = upload.json()["guid"]

        response = admin_client.get(
            f"/get/image/{guid}", params={"thumbnail": "true"}, follow_redirects=False
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/webp")
        assert response.headers["cache-control"] == IMAGE_CACHE_CONTROL

    def test_missing_guid_returns_404(self, client):
        missing = uuid4()
        response = client.get(f"/get/image/{missing}", follow_redirects=False)
        assert response.status_code == 404

    def test_invalid_guid_returns_422(self, client):
        response = client.get("/get/image/not-a-uuid", follow_redirects=False)
        assert response.status_code == 422
