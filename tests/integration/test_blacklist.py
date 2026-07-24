"""Do-not-index blacklist: inline check fragments, create/edit/bulk
enforcement, and the admin CRUD routes."""

from __future__ import annotations

from typing import cast

import pytest
from sqlalchemy import select

from pindb.database import Artist, BlacklistedName, BlacklistEntityType, Pin, Shop
from pindb.models.acquisition_type import AcquisitionType
from tests.factories.shop import ShopFactory

BLOCK_MESSAGE_SHOP: str = '"Sample Shop" Shop is not indexable at their request.'


def _blacklist(
    db_session,
    name: str,
    entity_type: BlacklistEntityType = BlacklistEntityType.shop,
    reason: str | None = None,
) -> BlacklistedName:
    entry = BlacklistedName(entity_type=entity_type, name=name, reason=reason)
    db_session.add(entry)
    db_session.flush()
    return entry


@pytest.mark.integration
class TestBlacklistNameCheck:
    def test_exact_match_returns_blocking_fragment(self, admin_client, db_session):
        _blacklist(db_session, "Sample Shop")

        response = admin_client.get(
            "/create/check-name",
            params={"kind": "shop", "name": "sample shop"},
        )

        assert response.status_code == 200
        assert "not indexable at their request" in response.text
        assert "cannot be submitted" in response.text
        assert "text-error-main" in response.text

    def test_fuzzy_match_returns_warning_fragment(self, admin_client, db_session):
        _blacklist(db_session, "Sample Shop")

        response = admin_client.get(
            "/create/check-name",
            params={"kind": "shop", "name": "Sampel Shop"},
        )

        assert response.status_code == 200
        assert "similar to" in response.text
        assert "Sample Shop" in response.text
        assert "do not submit unless certain" in response.text
        assert "text-pending-main" in response.text

    def test_artist_blacklist_only_hits_artist_kind(self, admin_client, db_session):
        _blacklist(db_session, "Sample Artist", entity_type=BlacklistEntityType.artist)

        artist_response = admin_client.get(
            "/create/check-name",
            params={"kind": "artist", "name": "Sample Artist"},
        )
        shop_response = admin_client.get(
            "/create/check-name",
            params={"kind": "shop", "name": "Sample Artist"},
        )

        assert "not indexable" in artist_response.text
        assert shop_response.text == ""

    def test_duplicate_beats_blacklist_feedback(
        self, admin_client, db_session, admin_user
    ):
        ShopFactory(name="Sample Shop", approved=True, created_by=admin_user)
        _blacklist(db_session, "Sample Shop")

        response = admin_client.get(
            "/create/check-name",
            params={"kind": "shop", "name": "Sample Shop"},
        )

        assert "already exists!" in response.text

    def test_unlisted_name_stays_clean(self, admin_client, db_session):
        _blacklist(db_session, "Sample Shop")

        response = admin_client.get(
            "/create/check-name",
            params={"kind": "shop", "name": "Totally Unrelated"},
        )

        assert response.text == ""


@pytest.mark.integration
class TestBlacklistCreateEnforcement:
    def test_create_shop_with_exact_match_is_refused(self, admin_client, db_session):
        _blacklist(db_session, "Sample Shop")

        response = admin_client.post(
            "/create/shop",
            data={"name": "sample shop"},
            follow_redirects=False,
        )

        assert response.status_code == 409
        assert BLOCK_MESSAGE_SHOP in response.text
        db_session.expire_all()
        assert db_session.scalar(select(Shop).where(Shop.name == "sample shop")) is None

    def test_create_shop_with_blacklisted_alias_is_refused(
        self, admin_client, db_session
    ):
        _blacklist(db_session, "Sample Shop")

        response = admin_client.post(
            "/create/shop",
            data={"name": "Fresh Vendor", "aliases": ["Sample Shop"]},
            follow_redirects=False,
        )

        assert response.status_code == 409
        db_session.expire_all()
        assert (
            db_session.scalar(select(Shop).where(Shop.name == "Fresh Vendor")) is None
        )

    def test_create_shop_with_similar_name_is_allowed(self, admin_client, db_session):
        _blacklist(db_session, "Sample Shop")

        response = admin_client.post(
            "/create/shop",
            data={"name": "Sampel Shop"},
            follow_redirects=False,
        )

        assert response.status_code == 200
        assert "HX-Redirect" in response.headers
        db_session.expire_all()
        assert (
            db_session.scalar(select(Shop).where(Shop.name == "Sampel Shop"))
            is not None
        )

    def test_create_artist_with_exact_match_is_refused(self, admin_client, db_session):
        _blacklist(db_session, "Sample Artist", entity_type=BlacklistEntityType.artist)

        response = admin_client.post(
            "/create/artist",
            data={"name": "Sample Artist"},
            follow_redirects=False,
        )

        assert response.status_code == 409
        db_session.expire_all()
        assert (
            db_session.scalar(select(Artist).where(Artist.name == "Sample Artist"))
            is None
        )


@pytest.mark.integration
class TestBlacklistBulkEnforcement:
    def test_bulk_row_with_blacklisted_shop_fails(
        self, admin_client, png_upload, db_session
    ):
        _blacklist(db_session, "Sample Shop")
        image_response = admin_client.post(
            "/bulk/pin/image", files={"image": png_upload}
        )
        front_guid = image_response.json()["guid"]

        response = admin_client.post(
            "/bulk/pin",
            json={
                "pins": [
                    {
                        "name": "Bulk Blocked Pin",
                        "acquisition_type": AcquisitionType.single.value,
                        "front_image_guid": front_guid,
                        "shop_names": ["Sample Shop"],
                    }
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["failed_count"] == 1
        assert "not indexable at their request" in data["results"][0]["error"]
        db_session.expire_all()
        assert (
            db_session.scalar(select(Pin).where(Pin.name == "Bulk Blocked Pin")) is None
        )
        assert db_session.scalar(select(Shop).where(Shop.name == "Sample Shop")) is None


@pytest.mark.integration
class TestBlacklistEditEnforcement:
    def test_rename_to_blacklisted_name_is_refused(
        self, admin_client, db_session, admin_user
    ):
        shop = cast(
            Shop,
            ShopFactory(name="Innocent Shop", approved=True, created_by=admin_user),
        )
        _blacklist(db_session, "Sample Shop")

        response = admin_client.post(
            f"/edit/shop/{shop.id}",
            data={"name": "Sample Shop"},
            follow_redirects=False,
        )

        assert response.status_code == 409
        db_session.expire_all()
        refreshed = db_session.get(Shop, shop.id)
        assert refreshed is not None
        assert refreshed.name == "Innocent Shop"

    def test_entity_predating_blacklist_stays_editable(
        self, admin_client, db_session, admin_user
    ):
        shop = cast(
            Shop, ShopFactory(name="Sample Shop", approved=True, created_by=admin_user)
        )
        _blacklist(db_session, "Sample Shop")

        response = admin_client.post(
            f"/edit/shop/{shop.id}",
            data={"name": "Sample Shop", "description": "updated"},
            follow_redirects=False,
        )

        assert response.status_code == 200
        assert "HX-Redirect" in response.headers
        db_session.expire_all()
        refreshed = db_session.get(Shop, shop.id)
        assert refreshed is not None
        assert refreshed.description == "updated"


@pytest.mark.integration
class TestBlacklistAdminRoutes:
    def test_page_lists_entries(self, admin_client, db_session):
        _blacklist(db_session, "Sample Shop", reason="asked via email")

        response = admin_client.get("/admin/blacklist")

        assert response.status_code == 200
        assert "Sample Shop" in response.text
        assert "asked via email" in response.text

    def test_add_both_creates_one_row_per_type(self, admin_client, db_session):
        response = admin_client.post(
            "/admin/blacklist",
            data={"name": "Dual Entity", "entity_type": "both", "reason": ""},
            follow_redirects=False,
        )

        assert response.status_code == 303
        db_session.expire_all()
        rows = (
            db_session.scalars(
                select(BlacklistedName).where(BlacklistedName.name == "Dual Entity")
            )
        ).all()
        assert {row.entity_type for row in rows} == {
            BlacklistEntityType.shop,
            BlacklistEntityType.artist,
        }

    def test_add_duplicate_is_idempotent(self, admin_client, db_session):
        _blacklist(db_session, "Sample Shop")

        response = admin_client.post(
            "/admin/blacklist",
            data={"name": "sample shop", "entity_type": "shop"},
            follow_redirects=False,
        )

        assert response.status_code == 303
        db_session.expire_all()
        rows = (
            db_session.scalars(
                select(BlacklistedName).where(
                    BlacklistedName.entity_type == BlacklistEntityType.shop,
                    BlacklistedName.normalized_name == "sample_shop",
                )
            )
        ).all()
        assert len(rows) == 1

    def test_delete_removes_row(self, admin_client, db_session):
        entry = _blacklist(db_session, "Sample Shop")
        entry_id: int = entry.id

        response = admin_client.post(
            f"/admin/blacklist/{entry_id}/delete",
            follow_redirects=False,
        )

        assert response.status_code == 303
        db_session.expire_all()
        assert db_session.get(BlacklistedName, entry_id) is None

    def test_non_admin_cannot_manage(self, editor_client):
        assert editor_client.get("/admin/blacklist").status_code in (302, 303, 401, 403)
