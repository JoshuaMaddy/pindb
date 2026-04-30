"""Tests for /admin/pending/** — queue, approve/reject/delete, cascade on Pin approval."""

import pytest
from sqlalchemy import select

from pindb.database import Artist, Pin, Shop, Tag
from tests.factories.artist import ArtistFactory
from tests.factories.pin import PinFactory
from tests.factories.shop import ShopFactory
from tests.factories.tag import TagFactory
from tests.integration.helpers.authz import assert_admin_only_get
from tests.integration.helpers.pending import INCLUDE_PENDING_AND_DELETED


@pytest.mark.integration
class TestPendingQueueAccess:
    def test_pending_queue_requires_admin(self, client, auth_client, editor_client):
        assert_admin_only_get("/admin/pending", client, auth_client, editor_client)

    def test_admin_returns_200(self, admin_client):
        assert admin_client.get("/admin/pending").status_code == 200

    def test_queue_lists_pending_shops_artists_tags(
        self, admin_client, db_session, editor_user
    ):
        ShopFactory(name="Pending Shop X", approved=False, created_by=editor_user)
        ArtistFactory(name="Pending Artist X", approved=False, created_by=editor_user)
        TagFactory(name="pending-tag-x", approved=False, created_by=editor_user)

        response = admin_client.get("/admin/pending")
        assert response.status_code == 200
        body = response.text
        assert "Pending Shop X" in body
        assert "Pending Artist X" in body
        assert "pending-tag-x" in body


@pytest.mark.integration
class TestApproveEndpoints:
    def test_approve_shop_sets_approved_at(self, admin_client, db_session, editor_user):
        shop = ShopFactory(approved=False, created_by=editor_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        response = admin_client.post(
            f"/admin/pending/approve/shop/{shop_id}", follow_redirects=False
        )
        assert response.status_code == 303

        db_session.expire_all()
        refreshed = db_session.scalar(
            select(Shop)
            .where(Shop.id == shop_id)
            .execution_options(**INCLUDE_PENDING_AND_DELETED)
        )
        assert refreshed is not None
        assert refreshed.approved_at is not None
        assert refreshed.approved_by_id is not None

    def test_approved_shop_visible_to_anonymous(
        self, admin_client, anon_client, db_session, editor_user
    ):
        """Visibility changes: before approval, anonymous cannot see the shop."""
        shop = ShopFactory(
            name="Approved Shop Visibility",
            approved=False,
            created_by=editor_user,
        )
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        before = anon_client.get(f"/get/shop/{shop_id}", follow_redirects=False)
        assert before.status_code in (302, 307, 404)

        admin_client.post(
            f"/admin/pending/approve/shop/{shop_id}", follow_redirects=False
        )

        after = anon_client.get(f"/get/shop/{shop_id}")
        assert after.status_code == 200
        assert "Approved Shop Visibility" in after.text

    def test_approve_unknown_entity_returns_404(self, admin_client):
        response = admin_client.post("/admin/pending/approve/shop/99999999")
        assert response.status_code == 404

    def test_cascade_approves_pending_shops_on_pin_approval(
        self, admin_client, db_session, editor_user
    ):
        """Approving a Pin cascades to pending shops/artists/tags on that pin."""
        shop = ShopFactory(approved=False, created_by=editor_user)
        artist = ArtistFactory(approved=False, created_by=editor_user)
        pin = PinFactory(
            approved=False,
            created_by=editor_user,
            shops={shop},
            artists={artist},
        )
        shop_id, artist_id, pin_id = shop.id, artist.id, pin.id  # ty:ignore[unresolved-attribute]

        response = admin_client.post(
            f"/admin/pending/approve/pin/{pin_id}", follow_redirects=False
        )
        assert response.status_code == 303

        db_session.expire_all()
        pin_after = db_session.scalar(
            select(Pin)
            .where(Pin.id == pin_id)
            .execution_options(**INCLUDE_PENDING_AND_DELETED)
        )
        shop_after = db_session.scalar(
            select(Shop)
            .where(Shop.id == shop_id)
            .execution_options(**INCLUDE_PENDING_AND_DELETED)
        )
        artist_after = db_session.scalar(
            select(Artist)
            .where(Artist.id == artist_id)
            .execution_options(**INCLUDE_PENDING_AND_DELETED)
        )
        assert pin_after is not None and pin_after.approved_at is not None
        assert shop_after is not None and shop_after.approved_at is not None
        assert artist_after is not None and artist_after.approved_at is not None


@pytest.mark.integration
class TestRejectEndpoint:
    def test_reject_shop_sets_rejected_at(self, admin_client, db_session, editor_user):
        shop = ShopFactory(approved=False, created_by=editor_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        response = admin_client.post(
            f"/admin/pending/reject/shop/{shop_id}", follow_redirects=False
        )
        assert response.status_code == 303

        db_session.expire_all()
        refreshed = db_session.scalar(
            select(Shop)
            .where(Shop.id == shop_id)
            .execution_options(**INCLUDE_PENDING_AND_DELETED)
        )
        assert refreshed is not None
        assert refreshed.rejected_at is not None
        assert refreshed.approved_at is None

    def test_rejected_shop_invisible_to_anonymous(
        self, admin_client, anon_client, db_session, editor_user
    ):
        shop = ShopFactory(approved=False, created_by=editor_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        admin_client.post(
            f"/admin/pending/reject/shop/{shop_id}", follow_redirects=False
        )

        response = anon_client.get(f"/get/shop/{shop_id}", follow_redirects=False)
        assert response.status_code in (302, 307, 404)


@pytest.mark.integration
class TestDeletePendingEndpoint:
    def test_delete_pending_shop_soft_deletes(
        self, admin_client, db_session, editor_user
    ):
        shop = ShopFactory(approved=False, created_by=editor_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        response = admin_client.post(
            f"/admin/pending/delete/shop/{shop_id}", follow_redirects=False
        )
        assert response.status_code == 303

        db_session.expire_all()
        refreshed = db_session.scalar(
            select(Shop)
            .where(Shop.id == shop_id)
            .execution_options(**INCLUDE_PENDING_AND_DELETED)
        )
        assert refreshed is not None
        assert refreshed.deleted_at is not None

    def test_delete_pending_tag_soft_deletes(
        self, admin_client, db_session, editor_user
    ):
        tag = TagFactory(approved=False, created_by=editor_user)
        tag_id = tag.id  # ty:ignore[unresolved-attribute]

        admin_client.post(f"/admin/pending/delete/tag/{tag_id}", follow_redirects=False)
        db_session.expire_all()
        refreshed = db_session.scalar(
            select(Tag)
            .where(Tag.id == tag_id)
            .execution_options(**INCLUDE_PENDING_AND_DELETED)
        )
        assert refreshed is not None
        assert refreshed.deleted_at is not None
