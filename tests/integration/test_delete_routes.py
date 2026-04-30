"""Admin-only soft-delete routes for each entity type.

All routes live under `/delete/{entity}/{id}` and:
 * accept POST only
 * redirect with 303
 * require admin (editor/user/guest → 403/401)
 * set `deleted_at` and `deleted_by_id` instead of issuing SQL DELETE
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from pindb.database import Artist, Pin, Shop, Tag
from tests.factories.artist import ArtistFactory
from tests.factories.pin import PinFactory
from tests.factories.shop import ShopFactory
from tests.factories.tag import TagFactory
from tests.integration.helpers.authz import assert_admin_only_post_loose_anon

_INCLUDE_DELETED = {"include_deleted": True}


def _refetch(db_session, model, id):
    db_session.expire_all()
    return db_session.scalar(
        select(model).where(model.id == id).execution_options(**_INCLUDE_DELETED)
    )


@pytest.mark.integration
class TestDeleteRoutesSuccess:
    def test_delete_pin(self, admin_client, db_session, admin_user):
        pin = PinFactory(approved=True, created_by=admin_user)
        pin_id = pin.id  # ty:ignore[unresolved-attribute]

        response = admin_client.post(f"/delete/pin/{pin_id}", follow_redirects=False)
        assert response.status_code == 303

        refreshed = _refetch(db_session, Pin, pin_id)
        assert refreshed is not None
        assert refreshed.deleted_at is not None
        assert refreshed.deleted_by_id == admin_user.id

    def test_delete_shop(self, admin_client, db_session, admin_user):
        shop = ShopFactory(approved=True, created_by=admin_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        response = admin_client.post(f"/delete/shop/{shop_id}", follow_redirects=False)
        assert response.status_code == 303

        refreshed = _refetch(db_session, Shop, shop_id)
        assert refreshed is not None
        assert refreshed.deleted_at is not None
        assert refreshed.deleted_by_id == admin_user.id

    def test_delete_artist(self, admin_client, db_session, admin_user):
        artist = ArtistFactory(approved=True, created_by=admin_user)
        artist_id = artist.id  # ty:ignore[unresolved-attribute]

        response = admin_client.post(
            f"/delete/artist/{artist_id}", follow_redirects=False
        )
        assert response.status_code == 303

        refreshed = _refetch(db_session, Artist, artist_id)
        assert refreshed is not None
        assert refreshed.deleted_at is not None
        assert refreshed.deleted_by_id == admin_user.id

    def test_delete_tag(self, admin_client, db_session, admin_user):
        tag = TagFactory(approved=True, created_by=admin_user)
        tag_id = tag.id  # ty:ignore[unresolved-attribute]

        response = admin_client.post(f"/delete/tag/{tag_id}", follow_redirects=False)
        assert response.status_code == 303

        refreshed = _refetch(db_session, Tag, tag_id)
        assert refreshed is not None
        assert refreshed.deleted_at is not None
        assert refreshed.deleted_by_id == admin_user.id


_DELETE_PATHS = (
    "/delete/pin/1",
    "/delete/shop/1",
    "/delete/artist/1",
    "/delete/tag/1",
)


@pytest.mark.integration
class TestDeleteRoutesAuthorization:
    @pytest.mark.parametrize("path", _DELETE_PATHS)
    def test_non_admin_rejected(
        self, anon_client, auth_client, editor_client, path: str
    ) -> None:
        assert_admin_only_post_loose_anon(path, anon_client, auth_client, editor_client)


@pytest.mark.integration
class TestDeleteRoutesIdempotency:
    def test_deleting_missing_entity_is_noop_redirect(self, admin_client):
        response = admin_client.post("/delete/shop/9999999", follow_redirects=False)
        assert response.status_code == 303

    def test_soft_deleted_entity_hidden_from_default_queries(
        self, admin_client, anon_client, db_session, admin_user
    ):
        shop = ShopFactory(name="Will Vanish", approved=True, created_by=admin_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        admin_client.post(f"/delete/shop/{shop_id}", follow_redirects=False)
        db_session.expire_all()

        # Default query: shop is hidden.
        found = db_session.scalar(select(Shop).where(Shop.id == shop_id))
        assert found is None

        # Bypass: row still exists in DB.
        found_with_opts = db_session.scalar(
            select(Shop).where(Shop.id == shop_id).execution_options(**_INCLUDE_DELETED)
        )
        assert found_with_opts is not None
