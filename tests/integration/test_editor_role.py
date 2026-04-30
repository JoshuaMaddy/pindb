"""Editor role semantics: pending creation, visibility, assert_editor_can_edit."""

import pytest
from sqlalchemy import select

from pindb.database import Shop
from tests.factories.shop import ShopFactory
from tests.integration.helpers.pending import INCLUDE_PENDING_AND_DELETED


@pytest.mark.integration
class TestEditorCanAccessCreateRoutes:
    def test_editor_get_create_pin(self, editor_client):
        assert editor_client.get("/create/pin").status_code == 200

    def test_editor_get_create_shop(self, editor_client):
        assert editor_client.get("/create/shop").status_code == 200


@pytest.mark.integration
class TestEditorCreatesPendingEntity:
    def test_editor_created_shop_is_pending(self, editor_client, db_session):
        response = editor_client.post(
            "/create/shop",
            data={"name": "Editor Pending Shop", "description": ""},
            follow_redirects=False,
        )
        assert response.status_code == 200

        db_session.expire_all()
        shop = db_session.scalar(
            select(Shop)
            .where(Shop.name == "Editor Pending Shop")
            .execution_options(**INCLUDE_PENDING_AND_DELETED)
        )
        assert shop is not None
        assert shop.approved_at is None
        assert shop.rejected_at is None

    def test_admin_created_shop_is_auto_approved(self, admin_client, db_session):
        response = admin_client.post(
            "/create/shop",
            data={"name": "Admin Approved Shop", "description": ""},
            follow_redirects=False,
        )
        assert response.status_code == 200

        db_session.expire_all()
        shop = db_session.scalar(
            select(Shop)
            .where(Shop.name == "Admin Approved Shop")
            .execution_options(**INCLUDE_PENDING_AND_DELETED)
        )
        assert shop is not None
        assert shop.approved_at is not None


@pytest.mark.integration
class TestPendingVisibility:
    def test_anonymous_cannot_see_pending_shop_in_list(
        self, anon_client, editor_user, db_session
    ):
        ShopFactory(
            name="Invisible Pending Shop",
            approved=False,
            created_by=editor_user,
        )
        response = anon_client.get("/list/shops")
        assert response.status_code == 200
        assert "Invisible Pending Shop" not in response.text

    def test_editor_sees_pending_shop_in_list(
        self, editor_client, editor_user, db_session
    ):
        ShopFactory(
            name="Editor Sees This Pending Shop",
            approved=False,
            created_by=editor_user,
        )
        response = editor_client.get("/list/shops")
        assert response.status_code == 200
        assert "Editor Sees This Pending Shop" in response.text


@pytest.mark.integration
class TestEditorCanEditGuard:
    """`assert_editor_can_edit` via `GET /edit/shop/{id}`."""

    def test_editor_can_edit_own_pending_shop(
        self, editor_client, editor_user, db_session
    ):
        shop = ShopFactory(approved=False, created_by=editor_user)
        response = editor_client.get(f"/edit/shop/{shop.id}")  # ty:ignore[unresolved-attribute]
        assert response.status_code == 200

    def test_editor_cannot_edit_other_editors_pending_shop(
        self, editor_client, other_editor_user, db_session
    ):
        shop = ShopFactory(approved=False, created_by=other_editor_user)
        response = editor_client.get(f"/edit/shop/{shop.id}")  # ty:ignore[unresolved-attribute]
        assert response.status_code == 403

    def test_editor_cannot_see_rejected_shop_via_edit(
        self, editor_client, editor_user, db_session
    ):
        """Rejected entries are filtered out entirely from the editor's view."""
        from datetime import datetime, timezone

        shop = ShopFactory(approved=False, created_by=editor_user)
        shop.rejected_at = datetime.now(timezone.utc).replace(tzinfo=None)  # ty:ignore[unresolved-attribute]
        shop.rejected_by_id = None  # ty:ignore[unresolved-attribute]
        db_session.flush()

        response = editor_client.get(f"/edit/shop/{shop.id}")  # ty:ignore[unresolved-attribute]
        # Rejected shops are filtered by `_filter_deleted` (rejected_at IS NULL
        # for editors), so the edit route returns 404.
        assert response.status_code == 404

    def test_editor_can_open_edit_for_approved_shop(
        self, editor_client, admin_user, db_session
    ):
        """Editor opening an approved shop enters the pending-edit flow."""
        shop = ShopFactory(name="Approved Shop", approved=True, created_by=admin_user)
        response = editor_client.get(f"/edit/shop/{shop.id}")  # ty:ignore[unresolved-attribute]
        assert response.status_code == 200

    def test_admin_can_edit_anything(self, admin_client, editor_user, db_session):
        shop = ShopFactory(approved=False, created_by=editor_user)
        response = admin_client.get(f"/edit/shop/{shop.id}")  # ty:ignore[unresolved-attribute]
        assert response.status_code == 200
