"""Happy-path create + edit flows for the supporting entity types (shop,
artist, tag). Pin routes are covered in ``test_routes_pin.py``."""

from __future__ import annotations

from typing import cast

import pytest
from sqlalchemy import select

from pindb.database import Artist, Shop, Tag
from pindb.database.tag import TagCategory
from tests.factories.artist import ArtistFactory
from tests.factories.shop import ShopFactory
from tests.factories.tag import TagFactory
from tests.integration.helpers.pending import INCLUDE_PENDING_ONLY


def _refetch(db_session, model, id):
    db_session.expire_all()
    return db_session.scalar(
        select(model).where(model.id == id).execution_options(**INCLUDE_PENDING_ONLY)
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

    def test_two_shops_may_share_same_alias_string(self, db_session, admin_user):
        s1 = cast(
            Shop,
            ShopFactory(
                name="Alias Shop One",
                approved=True,
                created_by=admin_user,
                aliases=["Shared"],
            ),
        )
        s2 = cast(
            Shop,
            ShopFactory(
                name="Alias Shop Two",
                approved=True,
                created_by=admin_user,
                aliases=["Shared"],
            ),
        )
        db_session.flush()
        assert {a.alias for a in s1.aliases} == {"Shared"}
        assert {a.alias for a in s2.aliases} == {"Shared"}


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

    def test_two_artists_may_share_same_alias_string(self, db_session, admin_user):
        a1 = cast(
            Artist,
            ArtistFactory(
                name="Artist Alias One",
                approved=True,
                created_by=admin_user,
                aliases=["Shared"],
            ),
        )
        a2 = cast(
            Artist,
            ArtistFactory(
                name="Artist Alias Two",
                approved=True,
                created_by=admin_user,
                aliases=["Shared"],
            ),
        )
        db_session.flush()
        assert {x.alias for x in a1.aliases} == {"Shared"}
        assert {x.alias for x in a2.aliases} == {"Shared"}


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


@pytest.mark.integration
class TestDuplicateTag:
    """`/create/tag?duplicate_from=<id>` prefills the form from an existing tag."""

    def test_duplicate_from_unknown_tag_returns_404(self, editor_client):
        response = editor_client.get("/create/tag?duplicate_from=999999")
        assert response.status_code == 404

    def test_duplicate_prefills_name_aliases_category_and_implications(
        self, editor_client, db_session, admin_user
    ):
        parent = TagFactory(name="parent_for_dup", approved=True, created_by=admin_user)
        source = TagFactory(
            name="source_tag_dup",
            approved=True,
            created_by=admin_user,
            aliases=["alias_one"],
            category=TagCategory.color,
        )
        source.implications.add(parent)  # ty:ignore[unresolved-attribute]
        db_session.flush()

        response = editor_client.get(
            f"/create/tag?duplicate_from={source.id}"  # ty:ignore[unresolved-attribute]
        )
        assert response.status_code == 200
        body = response.text
        assert "Create a Tag" in body
        assert "Duplicating" in body
        assert "Source Tag Dup" in body
        assert "alias_one" in body
        assert TagCategory.color.value in body
        # Implication options use canonical tag.name (underscores), not display_name.
        assert "parent_for_dup" in body

    def test_duplicate_requires_editor(self, auth_client, db_session, admin_user):
        source = TagFactory(approved=True, created_by=admin_user)
        response = auth_client.get(
            f"/create/tag?duplicate_from={source.id}"  # ty:ignore[unresolved-attribute]
        )
        assert response.status_code == 403

    def test_tag_page_shows_duplicate_link_to_editor(
        self, editor_client, db_session, admin_user
    ):
        tag = TagFactory(name="has_dup_btn", approved=True, created_by=admin_user)
        response = editor_client.get(
            f"/get/tag/{tag.id}"  # ty:ignore[unresolved-attribute]
        )
        assert response.status_code == 200
        assert (
            f"/create/tag?duplicate_from={tag.id}"  # ty:ignore[unresolved-attribute]
            in response.text
        )

    def test_tag_page_hides_duplicate_link_from_regular_user(
        self, auth_client, db_session, admin_user
    ):
        tag = TagFactory(name="no_dup_btn", approved=True, created_by=admin_user)
        response = auth_client.get(
            f"/get/tag/{tag.id}"  # ty:ignore[unresolved-attribute]
        )
        assert response.status_code == 200
        assert "duplicate_from" not in response.text
