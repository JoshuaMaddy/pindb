"""Deep integration coverage for pending approval/edit-chain routes."""

from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pindb.database import Artist, Pin, Shop, Tag
from tests.factories.artist import ArtistFactory
from tests.factories.pin import PinFactory
from tests.factories.shop import ShopFactory
from tests.factories.tag import TagFactory
from tests.integration.helpers.pending import pending_name_edit, set_bulk_id


@pytest.mark.integration
class TestPendingQueueRenderingBranches:
    def test_pending_queue_renders_bulk_grouped_entities_and_edits(
        self, admin_client, db_session, editor_user, admin_user
    ):
        bulk_id = uuid4()
        pending_shop = ShopFactory(
            name="queue_bulk_shop",
            approved=False,
            created_by=editor_user,
        )
        set_bulk_id(pending_shop, bulk_id)

        canonical_artist = ArtistFactory(
            name="queue_bulk_artist_canonical",
            approved=True,
            created_by=admin_user,
        )
        db_session.add(
            pending_name_edit(
                entity_type="artists",
                entity_id=canonical_artist.id,  # ty:ignore[unresolved-attribute]
                old_name="queue_bulk_artist_canonical",
                new_name="queue_bulk_artist_pending",
                created_by_id=editor_user.id,
                bulk_id=bulk_id,
            )
        )
        db_session.flush()

        response = admin_client.get("/admin/pending")
        assert response.status_code == 200
        assert "queue_bulk_shop" in response.text
        assert str(bulk_id) in response.text


@pytest.mark.integration
class TestPendingApproveEditEntityTypes:
    def test_approve_tag_edits_applies_snapshot(
        self, editor_client, admin_client, admin_user, db_session
    ):
        implied = cast(Tag, TagFactory(name="deep_implied"))
        tag = TagFactory(name="deep_tag_original", approved=True, created_by=admin_user)

        editor_client.post(
            f"/edit/tag/{tag.id}",  # ty:ignore[unresolved-attribute]
            data={
                "name": "deep_tag_pending",
                "description": "updated tag description",
                "category": "general",
                "implication_ids": [str(implied.id)],
                "aliases": ["deep_alias_tag"],
            },
            follow_redirects=False,
        )

        approve = admin_client.post(
            f"/admin/pending/approve-edits/tag/{tag.id}",  # ty:ignore[unresolved-attribute]
            follow_redirects=False,
        )
        assert approve.status_code == 303

        db_session.expire_all()
        refreshed = db_session.scalar(
            select(Tag)
            .where(Tag.id == tag.id)  # ty:ignore[unresolved-attribute]
            .options(selectinload(Tag.implications), selectinload(Tag.aliases))
            .execution_options(include_pending=True)
        )
        assert refreshed is not None
        assert refreshed.name == "deep_tag_pending"
        assert any(alias.alias == "deep_alias_tag" for alias in refreshed.aliases)
        assert any(
            implied_tag.id == implied.id for implied_tag in refreshed.implications
        )

    def test_approve_artist_edits_applies_snapshot(
        self, editor_client, admin_client, admin_user, db_session
    ):
        artist = ArtistFactory(
            name="deep_artist_original",
            approved=True,
            created_by=admin_user,
        )

        editor_client.post(
            f"/edit/artist/{artist.id}",  # ty:ignore[unresolved-attribute]
            data={
                "name": "deep_artist_pending",
                "description": "artist desc",
                "links": ["https://example.com/artist"],
                "aliases": ["artist_alias_pending"],
            },
            follow_redirects=False,
        )

        approve = admin_client.post(
            f"/admin/pending/approve-edits/artist/{artist.id}",  # ty:ignore[unresolved-attribute]
            follow_redirects=False,
        )
        assert approve.status_code == 303

        db_session.expire_all()
        refreshed = db_session.scalar(
            select(Artist)
            .where(Artist.id == artist.id)  # ty:ignore[unresolved-attribute]
            .options(selectinload(Artist.links), selectinload(Artist.aliases))
            .execution_options(include_pending=True)
        )
        assert refreshed is not None
        assert refreshed.name == "deep_artist_pending"
        assert any(
            link.path == "https://example.com/artist" for link in refreshed.links
        )

    def test_approve_pin_edits_cascades_pending_dependencies(
        self, editor_client, admin_client, editor_user, db_session
    ):
        pending_shop = ShopFactory(
            name="deep_pending_shop",
            approved=False,
            created_by=editor_user,
        )
        pin = PinFactory(
            name="deep_pin_original",
            approved=True,
            created_by=editor_user,
            shops={pending_shop},
        )
        pin_id = pin.id  # ty:ignore[unresolved-attribute]

        editor_client.post(
            f"/edit/pin/{pin_id}",
            data={
                "name": "deep_pin_pending_name",
                "acquisition_type": "single",
                "grade_names": ["Normal"],
                "grade_prices": [""],
                "currency_id": "999",
                "shop_ids": [str(pending_shop.id)],  # ty:ignore[unresolved-attribute]
                "tag_ids": [],
                "artist_ids": [],
                "pin_sets_ids": [],
                "variant_pin_ids": [],
                "unauthorized_copy_pin_ids": [],
                "posts": "1",
            },
            follow_redirects=False,
        )

        approve = admin_client.post(
            f"/admin/pending/approve-edits/pin/{pin_id}",
            follow_redirects=False,
        )
        assert approve.status_code == 303

        db_session.expire_all()
        refreshed_pin = db_session.scalar(
            select(Pin).where(Pin.id == pin_id).execution_options(include_pending=True)
        )
        refreshed_shop = db_session.scalar(
            select(Shop)
            .where(Shop.id == pending_shop.id)  # ty:ignore[unresolved-attribute]
            .execution_options(include_pending=True)
        )
        assert refreshed_pin is not None
        assert refreshed_pin.name == "deep_pin_pending_name"
        assert refreshed_shop is not None
        assert refreshed_shop.approved_at is not None
