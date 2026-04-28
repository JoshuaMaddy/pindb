"""`/bulk/pin*` routes: image upload, JSON pin creation, and per-entity-type
options lookup. Bulk pin import is admin-only; ``/bulk/options/*`` stays
editor-accessible for tag/pin forms. Admin submissions auto-approve."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from pindb.database import Pin
from pindb.models.acquisition_type import AcquisitionType


@pytest.mark.integration
class TestBulkPinAuthorization:
    def test_guest_rejected(self, anon_client):
        response = anon_client.get("/bulk/pin")
        assert response.status_code in (401, 403)

    def test_regular_user_rejected(self, auth_client):
        response = auth_client.get("/bulk/pin")
        assert response.status_code == 403

    def test_editor_rejected(self, editor_client):
        response = editor_client.get("/bulk/pin")
        assert response.status_code == 403

    def test_admin_allowed(self, admin_client):
        response = admin_client.get("/bulk/pin")
        assert response.status_code == 200


@pytest.mark.integration
class TestBulkImageUpload:
    def test_editor_rejected(self, editor_client, png_upload):
        response = editor_client.post(
            "/bulk/pin/image",
            files={"image": png_upload},
        )
        assert response.status_code == 403

    def test_upload_returns_guid(self, admin_client, png_upload):
        response = admin_client.post(
            "/bulk/pin/image",
            files={"image": png_upload},
        )
        assert response.status_code == 200
        data = response.json()
        assert "guid" in data
        assert len(data["guid"]) == 36


@pytest.mark.integration
class TestBulkPinsCreate:
    def test_editor_post_rejected(self, editor_client):
        response = editor_client.post("/bulk/pin", json={"pins": []})
        assert response.status_code == 403

    def test_single_pin_created(self, admin_client, png_upload, db_session):
        image_response = admin_client.post(
            "/bulk/pin/image", files={"image": png_upload}
        )
        front_guid = image_response.json()["guid"]

        response = admin_client.post(
            "/bulk/pin",
            json={
                "pins": [
                    {
                        "name": "Bulk Pin 1",
                        "acquisition_type": AcquisitionType.single.value,
                        "front_image_guid": front_guid,
                        "shop_names": ["Bulk Shop"],
                        "tag_names": ["Bulk Tag"],
                        "artist_names": ["Bulk Artist"],
                    }
                ]
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created_count"] == 1
        assert data["failed_count"] == 0
        assert data["results"][0]["success"] is True

        db_session.expire_all()
        pin = db_session.scalar(select(Pin).where(Pin.name == "Bulk Pin 1"))
        assert pin is not None

    def test_row_with_bad_guid_is_isolated(self, admin_client, png_upload, db_session):
        image_response = admin_client.post(
            "/bulk/pin/image", files={"image": png_upload}
        )
        good_guid = image_response.json()["guid"]

        response = admin_client.post(
            "/bulk/pin",
            json={
                "pins": [
                    {
                        "name": "Good Pin",
                        "acquisition_type": AcquisitionType.single.value,
                        "front_image_guid": good_guid,
                    },
                    {
                        "name": "Bad Pin",
                        "acquisition_type": AcquisitionType.single.value,
                        "front_image_guid": "not-a-guid",
                    },
                ]
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created_count"] == 1
        assert data["failed_count"] == 1
        good, bad = data["results"]
        assert good["success"] is True
        assert bad["success"] is False
        assert bad["error"]


@pytest.mark.integration
class TestBulkCreationBulkId:
    def test_admin_pins_in_one_submission_share_bulk_id(
        self, admin_client, png_upload, db_session
    ):
        image_one = admin_client.post(
            "/bulk/pin/image", files={"image": png_upload}
        ).json()["guid"]
        image_two = admin_client.post(
            "/bulk/pin/image", files={"image": png_upload}
        ).json()["guid"]

        response = admin_client.post(
            "/bulk/pin",
            json={
                "pins": [
                    {
                        "name": "Admin Bulk Pair 1",
                        "acquisition_type": AcquisitionType.single.value,
                        "front_image_guid": image_one,
                        "shop_names": ["Shared Admin Shop"],
                    },
                    {
                        "name": "Admin Bulk Pair 2",
                        "acquisition_type": AcquisitionType.single.value,
                        "front_image_guid": image_two,
                        "shop_names": ["Shared Admin Shop"],
                    },
                ]
            },
        )
        assert response.status_code == 200
        assert response.json()["created_count"] == 2

        db_session.expire_all()
        pins = db_session.scalars(
            select(Pin).where(Pin.name.in_(["Admin Bulk Pair 1", "Admin Bulk Pair 2"]))
        ).all()
        assert len(pins) == 2
        bulk_ids = {pin.bulk_id for pin in pins}
        assert len(bulk_ids) == 1
        assert next(iter(bulk_ids)) is not None
        assert all(pin.approved_at is not None for pin in pins)

    def test_admin_pins_auto_approve(self, admin_client, png_upload, db_session):
        front_guid = admin_client.post(
            "/bulk/pin/image", files={"image": png_upload}
        ).json()["guid"]

        response = admin_client.post(
            "/bulk/pin",
            json={
                "pins": [
                    {
                        "name": "Admin Bulk",
                        "acquisition_type": AcquisitionType.single.value,
                        "front_image_guid": front_guid,
                    }
                ]
            },
        )
        assert response.status_code == 200

        db_session.expire_all()
        pin = db_session.scalar(select(Pin).where(Pin.name == "Admin Bulk"))
        assert pin is not None
        assert pin.approved_at is not None


@pytest.mark.integration
class TestBulkOptionsLookup:
    def test_shop_options_lookup_by_substring(
        self, admin_client, db_session, admin_user
    ):
        from tests.factories.shop import ShopFactory

        ShopFactory(name="Alpha Shop", approved=True, created_by=admin_user)
        ShopFactory(name="Beta Shop", approved=True, created_by=admin_user)
        db_session.flush()

        response = admin_client.get("/bulk/options/shop", params={"q": "Alpha"})
        assert response.status_code == 200
        names = [row["value"] for row in response.json()]
        assert "Alpha Shop" in names
        assert "Beta Shop" not in names

    def test_editor_can_query_tag_options(self, editor_client):
        response = editor_client.get("/bulk/options/tag", params={"q": ""})
        assert response.status_code == 200
        assert isinstance(response.json(), list)
