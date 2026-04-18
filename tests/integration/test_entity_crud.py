"""Happy-path create + edit flows for the supporting entity types (shop,
artist, tag). Pin CRUD is covered separately in `test_pin_crud.py`."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from pindb.database import Artist, Shop, Tag
from pindb.database.tag import TagCategory
from tests.factories.artist import ArtistFactory
from tests.factories.shop import ShopFactory
from tests.factories.tag import TagFactory

_PENDING_OPTS = {"include_pending": True}


def _refetch(db_session, model, id):
    db_session.expire_all()
    return db_session.scalar(
        select(model).where(model.id == id).execution_options(**_PENDING_OPTS)
    )


@pytest.mark.integration
class TestShopCrud:
    def test_admin_create_shop_autoapproved(self, admin_client, db_session):
        response = admin_client.post(
            "/create/shop",
            data={
                "name": "Big Shop",
                "description": "sells things",
                "aliases": ["Big"],
            },
            follow_redirects=False,
        )
        assert response.status_code == 200
        assert "HX-Redirect" in response.headers

        db_session.expire_all()
        shop = db_session.scalar(select(Shop).where(Shop.name == "Big Shop"))
        assert shop is not None
        assert shop.approved_at is not None
        assert shop.description == "sells things"

    def test_admin_edit_shop_mutates_canonical_row(
        self, admin_client, db_session, admin_user
    ):
        shop = ShopFactory(name="Before", approved=True, created_by=admin_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        response = admin_client.post(
            f"/edit/shop/{shop_id}",
            data={"name": "After", "description": "updated"},
            follow_redirects=False,
        )
        assert response.status_code == 200
        assert "HX-Redirect" in response.headers

        refreshed = _refetch(db_session, Shop, shop_id)
        assert refreshed is not None
        assert refreshed.name == "After"
        assert refreshed.description == "updated"


@pytest.mark.integration
class TestArtistCrud:
    def test_admin_create_artist_autoapproved(self, admin_client, db_session):
        response = admin_client.post(
            "/create/artist",
            data={"name": "Picasso", "description": ""},
            follow_redirects=False,
        )
        assert response.status_code == 200

        db_session.expire_all()
        artist = db_session.scalar(select(Artist).where(Artist.name == "Picasso"))
        assert artist is not None
        assert artist.approved_at is not None

    def test_admin_edit_artist_mutates_canonical_row(
        self, admin_client, db_session, admin_user
    ):
        artist = ArtistFactory(name="Van Gogh", approved=True, created_by=admin_user)
        artist_id = artist.id  # ty:ignore[unresolved-attribute]

        response = admin_client.post(
            f"/edit/artist/{artist_id}",
            data={"name": "Vincent van Gogh", "description": ""},
            follow_redirects=False,
        )
        assert response.status_code == 200

        refreshed = _refetch(db_session, Artist, artist_id)
        assert refreshed is not None
        assert refreshed.name == "Vincent van Gogh"


@pytest.mark.integration
class TestTagCrud:
    def test_admin_create_tag_autoapproved_and_normalized(
        self, admin_client, db_session
    ):
        response = admin_client.post(
            "/create/tag",
            data={
                "name": "Rare Edition",
                "description": "hard to find",
                "category": TagCategory.general.value,
            },
            follow_redirects=False,
        )
        assert response.status_code == 200

        db_session.expire_all()
        tag = db_session.scalar(select(Tag).where(Tag.name == "rare_edition"))
        assert tag is not None
        assert tag.approved_at is not None
        assert tag.description == "hard to find"

    def test_admin_edit_tag_mutates_canonical_row(
        self, admin_client, db_session, admin_user
    ):
        tag = TagFactory(name="old_tag", approved=True, created_by=admin_user)
        tag_id = tag.id  # ty:ignore[unresolved-attribute]

        response = admin_client.post(
            f"/edit/tag/{tag_id}",
            data={
                "name": "new_tag",
                "description": "",
                "category": TagCategory.general.value,
            },
            follow_redirects=False,
        )
        assert response.status_code == 200

        refreshed = _refetch(db_session, Tag, tag_id)
        assert refreshed is not None
        assert refreshed.name == "new_tag"

    def test_duplicate_tag_name_htmx_returns_toast_signal(
        self, admin_client, db_session
    ):
        htmx_headers = {"HX-Request": "true", "HX-Target": "pindb-toast-host"}
        admin_client.post(
            "/create/tag",
            data={
                "name": "Unique Tag Name",
                "description": "",
                "category": TagCategory.general.value,
            },
            headers=htmx_headers,
            follow_redirects=False,
        )
        response = admin_client.post(
            "/create/tag",
            data={
                "name": "unique tag name",
                "description": "",
                "category": TagCategory.general.value,
            },
            headers=htmx_headers,
            follow_redirects=False,
        )
        assert response.status_code == 200
        assert "pindb-toast-signal" in response.text
        assert "That name or alias is already in use." in response.text
