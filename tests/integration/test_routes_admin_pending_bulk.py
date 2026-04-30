"""Integration coverage for ``/admin/pending/*-bulk/{bulk_id}`` routes."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from pindb.database import Artist, Shop, Tag
from pindb.database.pending_edit import PendingEdit
from tests.factories.artist import ArtistFactory
from tests.factories.shop import ShopFactory
from tests.factories.tag import TagFactory
from tests.integration.helpers.authz import assert_admin_only_post
from tests.integration.helpers.pending import pending_name_edit, set_bulk_id


@pytest.mark.integration
class TestAdminPendingBulkActions:
    def test_approve_bulk_applies_entity_and_edit_chain(
        self, admin_client, db_session, editor_user
    ):
        bulk_id = uuid4()
        shop = ShopFactory(
            approved=False, created_by=editor_user, name="Bulk Pending Shop"
        )
        set_bulk_id(shop, bulk_id)
        db_session.add(
            pending_name_edit(
                entity_type="shops",
                entity_id=shop.id,  # ty:ignore[unresolved-attribute]
                old_name="Bulk Pending Shop",
                new_name="Bulk Approved Shop",
                created_by_id=editor_user.id,
                bulk_id=bulk_id,
            )
        )
        db_session.flush()

        response = admin_client.post(
            f"/admin/pending/approve-bulk/{bulk_id}",
            follow_redirects=False,
        )
        assert response.status_code == 303

        db_session.expire_all()
        refreshed_shop = db_session.scalar(
            select(Shop)
            .where(Shop.id == shop.id)  # ty:ignore[unresolved-attribute]
            .execution_options(include_pending=True)
        )
        assert refreshed_shop is not None
        assert refreshed_shop.approved_at is not None
        assert refreshed_shop.name == "Bulk Approved Shop"

    def test_reject_bulk_marks_entities_and_edits_rejected(
        self, admin_client, db_session, editor_user
    ):
        bulk_id = uuid4()
        artist = ArtistFactory(
            approved=False,
            created_by=editor_user,
            name="Bulk Pending Artist",
        )
        set_bulk_id(artist, bulk_id)
        pending_edit = pending_name_edit(
            entity_type="artists",
            entity_id=artist.id,  # ty:ignore[unresolved-attribute]
            old_name="Bulk Pending Artist",
            new_name="Rejected Name",
            created_by_id=editor_user.id,
            bulk_id=bulk_id,
        )
        db_session.add(pending_edit)
        db_session.flush()

        response = admin_client.post(
            f"/admin/pending/reject-bulk/{bulk_id}",
            follow_redirects=False,
        )
        assert response.status_code == 303

        db_session.expire_all()
        refreshed_artist = db_session.scalar(
            select(Artist)
            .where(Artist.id == artist.id)  # ty:ignore[unresolved-attribute]
            .execution_options(include_pending=True)
        )
        assert refreshed_artist is not None
        assert refreshed_artist.rejected_at is not None

        refreshed_edit = db_session.get(PendingEdit, pending_edit.id)
        assert refreshed_edit is not None
        assert refreshed_edit.rejected_at is not None

    def test_delete_bulk_soft_deletes_entities_and_removes_edits(
        self, admin_client, db_session, editor_user
    ):
        bulk_id = uuid4()
        tag = TagFactory(approved=False, created_by=editor_user, name="bulk_delete_tag")
        set_bulk_id(tag, bulk_id)
        pending_edit = pending_name_edit(
            entity_type="tags",
            entity_id=tag.id,  # ty:ignore[unresolved-attribute]
            old_name="bulk_delete_tag",
            new_name="ignored_name",
            created_by_id=editor_user.id,
            bulk_id=bulk_id,
        )
        db_session.add(pending_edit)
        db_session.flush()
        pending_edit_id = pending_edit.id

        response = admin_client.post(
            f"/admin/pending/delete-bulk/{bulk_id}",
            follow_redirects=False,
        )
        assert response.status_code == 303

        db_session.expire_all()
        refreshed_tag = db_session.scalar(
            select(Tag)
            .where(Tag.id == tag.id)  # ty:ignore[unresolved-attribute]
            .execution_options(include_pending=True, include_deleted=True)
        )
        assert refreshed_tag is not None
        assert refreshed_tag.deleted_at is not None
        assert db_session.get(PendingEdit, pending_edit_id) is None


@pytest.mark.integration
class TestDeleteBulkPendingRoute:
    def test_delete_bulk_requires_admin(self, anon_client, auth_client, editor_client):
        bulk_id = uuid4()
        assert_admin_only_post(
            path=f"/admin/pending/delete-bulk/{bulk_id}",
            anon_client=anon_client,
            auth_client=auth_client,
            editor_client=editor_client,
        )

    def test_admin_delete_bulk_accepts_unknown_bulk_id(self, admin_client):
        response = admin_client.post(
            f"/admin/pending/delete-bulk/{uuid4()}",
            follow_redirects=False,
        )
        assert response.status_code == 303
