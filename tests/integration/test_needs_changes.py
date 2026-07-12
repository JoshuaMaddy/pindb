"""Tests for the needs-changes flow: a reviewer sends an entry back with a reason.

Covers the required change request, the notification message, who can still see and
edit the flagged entry, and the resubmit loop that returns it to the pending queue.
"""

import pytest
from sqlalchemy import select

from pindb.database import Shop
from pindb.database.message import Message, MessageCategory
from pindb.database.pending_edit import PendingEdit
from pindb.database.pending_mixin import MIN_CHANGE_REQUEST_LENGTH
from pindb.models.message_body import ChangesRequestedBody
from tests.factories.shop import ShopFactory
from tests.integration.helpers.pending import INCLUDE_PENDING_AND_DELETED

REASON = "The front image is blurry — please re-upload a sharper photo."


def _fetch_shop(db_session, shop_id: int) -> Shop | None:
    db_session.expire_all()
    return db_session.scalar(
        select(Shop)
        .where(Shop.id == shop_id)
        .execution_options(**INCLUDE_PENDING_AND_DELETED)
    )


@pytest.mark.integration
class TestChangeRequestIsRequired:
    def test_reason_shorter_than_minimum_is_rejected(
        self, admin_client, db_session, editor_user
    ):
        """A change request too short to act on is not a change request."""
        shop = ShopFactory(approved=False, created_by=editor_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        response = admin_client.post(
            f"/admin/pending/reject/shop/{shop_id}",
            data={"reason": "no"},
            follow_redirects=False,
        )
        assert response.status_code == 400

        refreshed = _fetch_shop(db_session, shop_id)
        assert refreshed is not None
        assert refreshed.rejected_at is None

    def test_whitespace_padding_does_not_satisfy_the_minimum(
        self, admin_client, db_session, editor_user
    ):
        """Padding with spaces is the obvious way around a length check; close it."""
        shop = ShopFactory(approved=False, created_by=editor_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        response = admin_client.post(
            f"/admin/pending/reject/shop/{shop_id}",
            data={"reason": "no" + " " * MIN_CHANGE_REQUEST_LENGTH},
            follow_redirects=False,
        )
        assert response.status_code == 400

        refreshed = _fetch_shop(db_session, shop_id)
        assert refreshed is not None
        assert refreshed.rejected_at is None

    def test_missing_reason_is_rejected(self, admin_client, db_session, editor_user):
        shop = ShopFactory(approved=False, created_by=editor_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        response = admin_client.post(
            f"/admin/pending/reject/shop/{shop_id}", follow_redirects=False
        )
        assert response.status_code == 422

        refreshed = _fetch_shop(db_session, shop_id)
        assert refreshed is not None
        assert refreshed.rejected_at is None


@pytest.mark.integration
class TestChangeRequestRecordsAndNotifies:
    def test_reason_is_stored_on_the_entity(
        self, admin_client, db_session, editor_user, admin_user
    ):
        shop = ShopFactory(approved=False, created_by=editor_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        admin_client.post(
            f"/admin/pending/reject/shop/{shop_id}",
            data={"reason": REASON},
            follow_redirects=False,
        )

        refreshed = _fetch_shop(db_session, shop_id)
        assert refreshed is not None
        assert refreshed.rejected_at is not None
        assert refreshed.rejected_by_id == admin_user.id
        assert refreshed.rejection_reason == REASON
        assert refreshed.approved_at is None

    def test_submitter_gets_a_message_deep_linked_to_the_entity(
        self, admin_client, db_session, editor_user, admin_user
    ):
        shop = ShopFactory(approved=False, created_by=editor_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        admin_client.post(
            f"/admin/pending/reject/shop/{shop_id}",
            data={"reason": REASON},
            follow_redirects=False,
        )

        db_session.expire_all()
        message = db_session.scalar(
            select(Message).where(Message.recipient_id == editor_user.id)
        )
        assert message is not None
        assert message.category == MessageCategory.changes_requested
        assert message.sender_id == admin_user.id
        assert message.related_entity_id == shop_id
        assert isinstance(message.body, ChangesRequestedBody)
        assert message.body.reason == REASON

    def test_no_message_when_the_submitter_is_unknown(self, admin_client, db_session):
        """An erased account nulls created_by_id; there is nobody left to notify."""
        shop = ShopFactory(approved=False, created_by=None)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        response = admin_client.post(
            f"/admin/pending/reject/shop/{shop_id}",
            data={"reason": REASON},
            follow_redirects=False,
        )
        assert response.status_code == 303

        db_session.expire_all()
        assert db_session.scalars(select(Message)).all() == []


@pytest.mark.integration
class TestNeedsChangesVisibility:
    def test_visible_to_the_submitting_editor(
        self, admin_client, editor_client, db_session, editor_user
    ):
        shop = ShopFactory(approved=False, created_by=editor_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        admin_client.post(
            f"/admin/pending/reject/shop/{shop_id}",
            data={"reason": REASON},
            follow_redirects=False,
        )

        response = editor_client.get(f"/get/shop/{shop_id}", follow_redirects=True)
        assert response.status_code == 200
        # The banner carries the reviewer's reason to the person who has to act on it.
        assert REASON in response.text

    def test_still_hidden_from_anonymous_visitors(
        self, admin_client, anon_client, db_session, editor_user
    ):
        shop = ShopFactory(approved=False, created_by=editor_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        admin_client.post(
            f"/admin/pending/reject/shop/{shop_id}",
            data={"reason": REASON},
            follow_redirects=False,
        )

        response = anon_client.get(f"/get/shop/{shop_id}", follow_redirects=False)
        assert response.status_code in (302, 307, 404)


@pytest.mark.integration
class TestResubmitLoop:
    def test_editing_a_flagged_entry_returns_it_to_pending(
        self, admin_client, editor_client, db_session, editor_user
    ):
        """The whole point of the flow: fix it, and it goes back in the queue."""
        shop = ShopFactory(approved=False, created_by=editor_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        admin_client.post(
            f"/admin/pending/reject/shop/{shop_id}",
            data={"reason": REASON},
            follow_redirects=False,
        )

        response = editor_client.post(
            f"/edit/shop/{shop_id}",
            data={"name": "Fixed Shop", "description": "Now with a description."},
            follow_redirects=False,
        )
        assert response.status_code == 200

        refreshed = _fetch_shop(db_session, shop_id)
        assert refreshed is not None
        assert refreshed.name == "Fixed Shop"
        assert refreshed.rejected_at is None
        assert refreshed.rejected_by_id is None
        assert refreshed.rejection_reason is None
        assert refreshed.approved_at is None  # pending again, not auto-approved

    def test_flagged_entry_is_back_in_the_admin_pending_queue(
        self, admin_client, editor_client, db_session, editor_user
    ):
        shop = ShopFactory(approved=False, created_by=editor_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        admin_client.post(
            f"/admin/pending/reject/shop/{shop_id}",
            data={"reason": REASON},
            follow_redirects=False,
        )
        editor_client.post(
            f"/edit/shop/{shop_id}",
            data={"name": "Requeued Shop", "description": "Fixed."},
            follow_redirects=False,
        )

        response = admin_client.get("/admin/pending")
        assert response.status_code == 200
        assert "Requeued Shop" in response.text
        # Back in the pending sections, so the reviewer's old reason is gone.
        assert REASON not in response.text


@pytest.mark.integration
class TestNeedsChangesEditChain:
    def test_rejected_edit_chain_reopens_on_resubmit(
        self, admin_client, editor_client, db_session, admin_user
    ):
        """A resubmitted edit stacks on the flagged chain instead of orphaning it."""
        shop = ShopFactory(name="Chain Shop", approved=True, created_by=admin_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        editor_client.post(
            f"/edit/shop/{shop_id}",
            data={"name": "First Rename", "description": ""},
            follow_redirects=False,
        )
        admin_client.post(
            f"/admin/pending/reject-edits/shop/{shop_id}",
            data={"reason": REASON},
            follow_redirects=False,
        )

        db_session.expire_all()
        flagged = db_session.scalars(
            select(PendingEdit).where(PendingEdit.entity_id == shop_id)
        ).all()
        assert len(flagged) == 1
        assert flagged[0].rejected_at is not None
        assert flagged[0].rejection_reason == REASON

        editor_client.post(
            f"/edit/shop/{shop_id}",
            data={"name": "Second Rename", "description": ""},
            follow_redirects=False,
        )

        db_session.expire_all()
        chain = db_session.scalars(
            select(PendingEdit)
            .where(PendingEdit.entity_id == shop_id)
            .order_by(PendingEdit.id)
        ).all()
        assert len(chain) == 2
        # The flagged edit was reopened rather than left behind, so the new edit
        # chains onto it and the admin reviews one coherent chain.
        assert all(edit.rejected_at is None for edit in chain)
        assert all(edit.rejection_reason is None for edit in chain)
        assert chain[1].parent_id == chain[0].id

    def test_flagged_edit_chain_can_still_be_approved(
        self, admin_client, editor_client, db_session, admin_user
    ):
        """A reviewer can change their mind: approving a flagged chain applies it.

        The chain helpers include needs-changes edits, so the Approve button in the
        Needs Changes section has a chain to apply rather than silently doing nothing.
        """
        shop = ShopFactory(name="Relent Shop", approved=True, created_by=admin_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        editor_client.post(
            f"/edit/shop/{shop_id}",
            data={"name": "Relent Renamed", "description": ""},
            follow_redirects=False,
        )
        admin_client.post(
            f"/admin/pending/reject-edits/shop/{shop_id}",
            data={"reason": REASON},
            follow_redirects=False,
        )
        admin_client.post(
            f"/admin/pending/approve-edits/shop/{shop_id}", follow_redirects=False
        )

        refreshed = _fetch_shop(db_session, shop_id)
        assert refreshed is not None
        assert refreshed.name == "Relent Renamed"

    def test_editor_sees_the_change_request_on_the_entity_page(
        self, admin_client, editor_client, db_session, admin_user
    ):
        """An edit rejection never touches the entity row, so the banner has to come
        from the flagged chain — otherwise the editor's only clue is their inbox."""
        shop = ShopFactory(name="Banner Shop", approved=True, created_by=admin_user)
        shop_id = shop.id  # ty:ignore[unresolved-attribute]

        editor_client.post(
            f"/edit/shop/{shop_id}",
            data={"name": "Banner Renamed", "description": ""},
            follow_redirects=False,
        )
        admin_client.post(
            f"/admin/pending/reject-edits/shop/{shop_id}",
            data={"reason": REASON},
            follow_redirects=False,
        )

        response = editor_client.get(f"/get/shop/{shop_id}", follow_redirects=True)
        assert response.status_code == 200
        assert REASON in response.text
        # ...and not the "awaiting approval" banner, which would point at the admin.
        assert "awaiting approval" not in response.text
