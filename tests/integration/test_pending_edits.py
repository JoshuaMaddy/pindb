"""PendingEdit chain flow: editor edits on approved entities don't mutate
the canonical row, they create PendingEdit rows that an admin approves later."""

import pytest
from sqlalchemy import select

from pindb.database import Shop
from pindb.database.pending_edit import PendingEdit
from tests.factories.shop import ShopFactory


def _pending_edits_for_shop(db_session, shop_id: int) -> list[PendingEdit]:
    return list(
        db_session.scalars(
            select(PendingEdit)
            .where(
                PendingEdit.entity_type == "shops",
                PendingEdit.entity_id == shop_id,
            )
            .order_by(PendingEdit.id.asc())
        ).all()
    )


@pytest.mark.integration
class TestEditorCreatesPendingEdit:
    def test_editor_edit_on_approved_shop_creates_pending_edit(
        self, editor_client, admin_user, db_session
    ):
        shop = ShopFactory(name="Original Name", approved=True, created_by=admin_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        response = editor_client.post(
            f"/edit/shop/{shop_id}",
            data={"name": "New Name From Editor", "description": ""},
            follow_redirects=False,
        )
        assert response.status_code == 200

        db_session.expire_all()

        canonical = db_session.scalar(select(Shop).where(Shop.id == shop_id))
        assert canonical is not None
        assert canonical.name == "Original Name"

        edits = _pending_edits_for_shop(db_session, shop_id)
        assert len(edits) == 1
        patch = edits[0].patch
        assert "name" in patch
        assert patch["name"]["old"] == "Original Name"
        assert patch["name"]["new"] == "New Name From Editor"
        assert edits[0].created_by_id is not None
        assert edits[0].approved_at is None

    def test_second_edit_extends_chain(self, editor_client, admin_user, db_session):
        shop = ShopFactory(name="V0", approved=True, created_by=admin_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        editor_client.post(
            f"/edit/shop/{shop_id}",
            data={"name": "V1", "description": ""},
            follow_redirects=False,
        )
        editor_client.post(
            f"/edit/shop/{shop_id}",
            data={"name": "V2", "description": ""},
            follow_redirects=False,
        )

        db_session.expire_all()
        edits = _pending_edits_for_shop(db_session, shop_id)
        assert len(edits) == 2
        # Second edit points at the first.
        assert edits[1].parent_id == edits[0].id

    def test_admin_edit_on_approved_shop_writes_directly(
        self, admin_client, admin_user, db_session
    ):
        """Admins bypass the pending-edit flow entirely."""
        shop = ShopFactory(name="Original", approved=True, created_by=admin_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        response = admin_client.post(
            f"/edit/shop/{shop_id}",
            data={"name": "Admin Direct Update", "description": ""},
            follow_redirects=False,
        )
        assert response.status_code == 200

        db_session.expire_all()
        canonical = db_session.scalar(select(Shop).where(Shop.id == shop_id))
        assert canonical is not None
        assert canonical.name == "Admin Direct Update"

        assert _pending_edits_for_shop(db_session, shop_id) == []


@pytest.mark.integration
class TestApprovePendingEdits:
    def test_approve_edits_writes_snapshot_to_canonical_row(
        self, editor_client, admin_client, admin_user, db_session
    ):
        shop = ShopFactory(name="Original", approved=True, created_by=admin_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        editor_client.post(
            f"/edit/shop/{shop_id}",
            data={"name": "Pending Rename", "description": ""},
            follow_redirects=False,
        )
        db_session.expire_all()
        assert len(_pending_edits_for_shop(db_session, shop_id)) == 1

        response = admin_client.post(
            f"/admin/pending/approve-edits/shop/{shop_id}", follow_redirects=False
        )
        assert response.status_code == 303

        db_session.expire_all()
        canonical = db_session.scalar(select(Shop).where(Shop.id == shop_id))
        assert canonical is not None
        assert canonical.name == "Pending Rename"

        # Edit is flagged approved, not deleted.
        edits = _pending_edits_for_shop(db_session, shop_id)
        assert len(edits) == 1
        assert edits[0].approved_at is not None


@pytest.mark.integration
class TestRejectPendingEdits:
    def test_reject_edits_marks_rejected_and_leaves_row_untouched(
        self, editor_client, admin_client, admin_user, db_session
    ):
        shop = ShopFactory(name="Keep Me", approved=True, created_by=admin_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        editor_client.post(
            f"/edit/shop/{shop_id}",
            data={"name": "Rejected Rename", "description": ""},
            follow_redirects=False,
        )

        response = admin_client.post(
            f"/admin/pending/reject-edits/shop/{shop_id}", follow_redirects=False
        )
        assert response.status_code == 303

        db_session.expire_all()
        canonical = db_session.scalar(select(Shop).where(Shop.id == shop_id))
        assert canonical is not None
        assert canonical.name == "Keep Me"

        edits = _pending_edits_for_shop(db_session, shop_id)
        assert len(edits) == 1
        assert edits[0].rejected_at is not None


@pytest.mark.integration
class TestDeletePendingEdits:
    def test_delete_edits_removes_chain(
        self, editor_client, admin_client, admin_user, db_session
    ):
        shop = ShopFactory(name="X", approved=True, created_by=admin_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        editor_client.post(
            f"/edit/shop/{shop_id}",
            data={"name": "Will Be Deleted", "description": ""},
            follow_redirects=False,
        )
        db_session.expire_all()
        assert len(_pending_edits_for_shop(db_session, shop_id)) == 1

        response = admin_client.post(
            f"/admin/pending/delete-edits/shop/{shop_id}", follow_redirects=False
        )
        assert response.status_code == 303

        db_session.expire_all()
        assert _pending_edits_for_shop(db_session, shop_id) == []
