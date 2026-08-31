"""The admin review bar for a pending *edit chain* on the entity's own page.

The queue lists an edit chain, but an admin who opens the entry to read the
proposed diff needs to rule on it without navigating back. Unlike the new-entry
bar, ruling on an edit leaves the page standing, so the posts carry
``?after=reload`` and htmx re-renders in place.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from pindb.database import Shop
from pindb.database.pending_edit import PendingEdit
from tests.factories.artist import ArtistFactory
from tests.factories.pin import PinFactory
from tests.factories.pin_set import PinSetFactory
from tests.factories.shop import ShopFactory
from tests.factories.tag import TagFactory
from tests.integration.helpers.pending import pending_name_edit

REASON = "Please say what this shop sells and where it ships from before this lands."


def _edits(db_session, shop_id: int) -> list[PendingEdit]:
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


def _shop_with_pending_edit(editor_client, admin_user, name: str) -> int:
    shop = ShopFactory(name=name, approved=True, created_by=admin_user)
    shop_id: int = shop.id  # ty:ignore[unresolved-attribute]
    editor_client.post(
        f"/edit/shop/{shop_id}",
        data={"name": f"{name} Proposed", "description": ""},
        follow_redirects=False,
    )
    return shop_id


@pytest.mark.integration
class TestEditReviewBarRendering:
    def test_admin_sees_the_edit_bar_on_an_entity_with_a_pending_chain(
        self, editor_client, admin_client, admin_user
    ):
        shop_id = _shop_with_pending_edit(editor_client, admin_user, "BarEditShop")

        page = admin_client.get(f"/get/shop/{shop_id}")
        assert page.status_code == 200
        assert "Pending edit awaiting review." in page.text
        assert f"/admin/pending/approve-edits/shop/{shop_id}?after=reload" in page.text
        assert f"/admin/pending/reject-edits/shop/{shop_id}?after=reload" in page.text
        assert f"/admin/pending/delete-edits/shop/{shop_id}?after=reload" in page.text

    def test_editor_does_not_see_the_edit_bar(self, editor_client, admin_user):
        shop_id = _shop_with_pending_edit(editor_client, admin_user, "BarEditorShop")

        page = editor_client.get(f"/get/shop/{shop_id}")
        assert page.status_code == 200
        assert "Pending edit awaiting review." not in page.text
        assert "/admin/pending/approve-edits/" not in page.text

    def test_no_bar_when_the_entity_has_no_pending_chain(
        self, admin_client, admin_user
    ):
        shop = ShopFactory(name="BarCleanShop", approved=True, created_by=admin_user)

        page = admin_client.get(f"/get/shop/{shop.id}")  # ty:ignore[unresolved-attribute]
        assert page.status_code == 200
        assert "Pending edit awaiting review." not in page.text
        assert "/admin/pending/approve-edits/" not in page.text

    def test_needs_changes_chain_drops_request_changes_from_the_bar(
        self, editor_client, admin_client, admin_user
    ):
        """A chain already sent back offers Approve and Discard only."""
        shop_id = _shop_with_pending_edit(editor_client, admin_user, "BarSentBackShop")
        admin_client.post(
            f"/admin/pending/reject-edits/shop/{shop_id}",
            data={"reason": REASON},
            follow_redirects=False,
        )

        page = admin_client.get(f"/get/shop/{shop_id}")
        assert page.status_code == 200
        assert "Edit sent back for changes — waiting on the submitter." in page.text
        assert f"/admin/pending/approve-edits/shop/{shop_id}?after=reload" in page.text
        assert f"/admin/pending/delete-edits/shop/{shop_id}?after=reload" in page.text
        assert "/admin/pending/reject-edits/" not in page.text


@pytest.mark.integration
class TestEditReviewBarActions:
    def test_approve_with_after_reload_applies_the_edit_and_refreshes(
        self, editor_client, admin_client, admin_user, db_session
    ):
        shop_id = _shop_with_pending_edit(editor_client, admin_user, "ReloadApprove")

        response = admin_client.post(
            f"/admin/pending/approve-edits/shop/{shop_id}?after=reload",
            headers={"HX-Request": "true"},
            follow_redirects=False,
        )
        assert response.status_code == 204
        assert response.headers["HX-Refresh"] == "true"
        assert response.text == ""

        db_session.expire_all()
        canonical = db_session.scalar(select(Shop).where(Shop.id == shop_id))
        assert canonical is not None
        assert canonical.name == "ReloadApprove Proposed"

    def test_request_changes_with_after_reload_flags_the_chain(
        self, editor_client, admin_client, admin_user, db_session
    ):
        shop_id = _shop_with_pending_edit(editor_client, admin_user, "ReloadReject")

        response = admin_client.post(
            f"/admin/pending/reject-edits/shop/{shop_id}?after=reload",
            data={"reason": REASON},
            headers={"HX-Request": "true"},
            follow_redirects=False,
        )
        assert response.status_code == 204
        assert response.headers["HX-Refresh"] == "true"

        db_session.expire_all()
        edits = _edits(db_session, shop_id)
        assert len(edits) == 1
        assert edits[0].rejected_at is not None
        assert edits[0].rejection_reason == REASON

        canonical = db_session.scalar(select(Shop).where(Shop.id == shop_id))
        assert canonical is not None
        assert canonical.name == "ReloadReject"

    def test_discard_with_after_reload_drops_the_chain_not_the_entity(
        self, editor_client, admin_client, admin_user, db_session
    ):
        shop_id = _shop_with_pending_edit(editor_client, admin_user, "ReloadDiscard")

        response = admin_client.post(
            f"/admin/pending/delete-edits/shop/{shop_id}?after=reload",
            headers={"HX-Request": "true"},
            follow_redirects=False,
        )
        assert response.status_code == 204
        assert response.headers["HX-Refresh"] == "true"

        db_session.expire_all()
        assert _edits(db_session, shop_id) == []
        canonical = db_session.scalar(select(Shop).where(Shop.id == shop_id))
        assert canonical is not None
        assert canonical.name == "ReloadDiscard"

    def test_no_js_post_still_redirects_to_the_queue(
        self, editor_client, admin_client, admin_user
    ):
        """The bare form fallback has no queue to swap and no htmx to refresh."""
        shop_id = _shop_with_pending_edit(editor_client, admin_user, "ReloadNoJs")

        response = admin_client.post(
            f"/admin/pending/approve-edits/shop/{shop_id}?after=reload",
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == "/admin/pending"

    def test_editor_cannot_post_the_edit_actions(
        self, editor_client, admin_user, db_session
    ):
        shop_id = _shop_with_pending_edit(editor_client, admin_user, "ReloadForbidden")

        response = editor_client.post(
            f"/admin/pending/approve-edits/shop/{shop_id}?after=reload",
            follow_redirects=False,
        )
        assert response.status_code in (401, 403)

        db_session.expire_all()
        canonical = db_session.scalar(select(Shop).where(Shop.id == shop_id))
        assert canonical is not None
        assert canonical.name == "ReloadForbidden"


@pytest.mark.integration
class TestEditReviewBarOnEveryEntityType:
    """All five detail pages render the bar — they are five separate templates."""

    @pytest.mark.parametrize(
        ("slug", "table", "factory"),
        [
            ("pin", "pins", PinFactory),
            ("shop", "shops", ShopFactory),
            ("artist", "artists", ArtistFactory),
            ("tag", "tags", TagFactory),
            ("pin_set", "pin_sets", PinSetFactory),
        ],
    )
    def test_bar_renders_on_each_detail_page(
        self, admin_client, db_session, admin_user, editor_user, slug, table, factory
    ):
        entity = factory(
            name=f"bar_{slug}_original", approved=True, created_by=admin_user
        )
        entity_id: int = entity.id
        db_session.add(
            pending_name_edit(
                entity_type=table,
                entity_id=entity_id,
                old_name=f"bar_{slug}_original",
                new_name=f"bar_{slug}_proposed",
                created_by_id=editor_user.id,
            )
        )
        db_session.flush()

        page = admin_client.get(f"/get/{slug}/{entity_id}", follow_redirects=True)
        assert page.status_code == 200
        assert "Pending edit awaiting review." in page.text
        assert (
            f"/admin/pending/approve-edits/{slug}/{entity_id}?after=reload" in page.text
        )
