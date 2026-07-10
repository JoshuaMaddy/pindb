"""Messages and per-user receipts: body typing, lazy broadcast inbox, audience
scoping, expiry, seen/read/archive upserts, and table constraints.

Receipts are created lazily, so the query helpers here mirror the intended route
logic: reads LEFT JOIN receipts for the current user and treat a missing row as
"unseen, unread, not archived"; writes UPSERT the receipt.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from pindb.database.change_log import ChangeLog
from pindb.database.entity_type import EntityType
from pindb.database.message import (
    Message,
    MessageAudience,
    MessageCategory,
    MessageReceipt,
)
from pindb.database.message_queries import (
    archive_statement,
    inbox_statement,
    mark_all_read_statement,
    mark_read_statement,
    unread_count_statement,
)
from pindb.database.user import User
from pindb.models.message_body import (
    ContributionBody,
    MessageBodyAdapter,
    PinRejectionBody,
    TextBody,
)
from pindb.templates.messages.render import message_target_url
from pindb.utils import utc_now

# --- Query helpers: thin sync wrappers over the production statement builders.
# These exercise the real inbox logic (``database.message_queries``) against the
# sync test session, so the behaviour asserted here is exactly what the routes run.


def _inbox(session: Session, user: User) -> list[Message]:
    """Non-archived visible messages, newest first."""
    return list(session.scalars(inbox_statement(user, limit=100, offset=0)).all())


def _unread_count(session: Session, user: User) -> int:
    """Count of visible, unread (``read_at IS NULL``), non-archived messages."""
    return session.scalar(unread_count_statement(user)) or 0


def _mark_read(session: Session, *, message_id: int, user_id: int) -> None:
    """Idempotently mark one message read (first-read timestamps preserved)."""
    session.execute(mark_read_statement(message_id=message_id, user_id=user_id))


def _mark_all_read(session: Session, user: User) -> None:
    """Mark every visible unread message read, creating receipts as needed."""
    session.execute(mark_all_read_statement(user))


def _archive(session: Session, *, message_id: int, user_id: int) -> None:
    """Archive a message for a user (creates the receipt on first archive)."""
    session.execute(archive_statement(message_id=message_id, user_id=user_id))


def _receipt_rows(session: Session, message_id: int) -> list[MessageReceipt]:
    return list(
        session.scalars(
            select(MessageReceipt).where(MessageReceipt.message_id == message_id)
        ).all()
    )


# --- Tests ------------------------------------------------------------------


@pytest.mark.integration
class TestMessageBodyRoundTrip:
    @pytest.mark.parametrize(
        "body",
        [
            TextBody(text="hello world"),
            TextBody(text="linked", redirect_url="/user/me#badges"),
            PinRejectionBody(reason="blurry image", pin_id=42),
            ContributionBody(summary="added 3 pins", points=3),
        ],
    )
    def test_body_survives_db_round_trip_as_typed_model(self, db_session, body):
        message = Message(category=MessageCategory.system, body=body)
        db_session.add(message)
        db_session.flush()
        message_id = message.id

        db_session.expire_all()
        reloaded = db_session.get(Message, message_id)

        assert reloaded is not None
        assert type(reloaded.body) is type(body)
        assert reloaded.body == body
        assert reloaded.body.redirect_url == body.redirect_url

    def test_redirect_url_defaults_to_none(self):
        assert TextBody(text="x").redirect_url is None

    def test_unknown_body_type_fails_validation(self):
        with pytest.raises(ValidationError):
            MessageBodyAdapter.validate_python({"type": "not_a_real_kind"})


@pytest.mark.integration
class TestMessageTargetUrl:
    def test_redirect_url_takes_precedence_over_entity(self):
        request = MagicMock()
        request.url_for.side_effect = AssertionError("url_for must not be called")
        message = Message(
            category=MessageCategory.pin_rejection,
            body=PinRejectionBody(reason="dupe", pin_id=7, redirect_url="/go"),
            related_entity_type=EntityType.pin,
            related_entity_id=7,
        )
        assert message_target_url(request, message) == "/go"

    def test_no_target_without_redirect_or_entity(self):
        request = MagicMock()
        request.url_for.side_effect = AssertionError("url_for must not be called")
        message = Message(
            category=MessageCategory.announcement,
            body=TextBody(text="plain"),
        )
        assert message_target_url(request, message) is None


@pytest.mark.integration
class TestLazyBroadcastInbox:
    def test_untouched_broadcast_is_unread_with_no_receipt_rows(
        self, db_session, admin_user
    ):
        message = Message(
            category=MessageCategory.announcement,
            body=TextBody(text="site-wide notice"),
        )
        db_session.add(message)
        db_session.flush()

        assert _receipt_rows(db_session, message.id) == []
        inbox = _inbox(db_session, admin_user)
        assert message.id in {item.id for item in inbox}
        assert _unread_count(db_session, admin_user) == 1

    def test_direct_message_to_other_user_is_not_visible(
        self, db_session, admin_user, editor_user
    ):
        direct = Message(
            category=MessageCategory.direct,
            body=TextBody(text="just for the editor"),
            recipient_id=editor_user.id,
        )
        db_session.add(direct)
        db_session.flush()

        assert direct.id not in {item.id for item in _inbox(db_session, admin_user)}
        assert direct.id in {item.id for item in _inbox(db_session, editor_user)}


@pytest.mark.integration
class TestAudienceAndExpiry:
    def test_editor_and_admin_audiences_are_scoped(
        self, db_session, admin_user, editor_user, test_user
    ):
        editors_only = Message(
            category=MessageCategory.announcement,
            body=TextBody(text="for editors"),
            audience=MessageAudience.editors,
        )
        admins_only = Message(
            category=MessageCategory.announcement,
            body=TextBody(text="for admins"),
            audience=MessageAudience.admins,
        )
        db_session.add_all([editors_only, admins_only])
        db_session.flush()

        regular_ids = {item.id for item in _inbox(db_session, test_user)}
        editor_ids = {item.id for item in _inbox(db_session, editor_user)}
        admin_ids = {item.id for item in _inbox(db_session, admin_user)}

        assert editors_only.id not in regular_ids
        assert admins_only.id not in regular_ids
        assert editors_only.id in editor_ids
        assert admins_only.id not in editor_ids
        assert editors_only.id in admin_ids
        assert admins_only.id in admin_ids

    def test_expired_broadcast_is_excluded(self, db_session, admin_user):
        expired = Message(
            category=MessageCategory.announcement,
            body=TextBody(text="old news"),
            expires_at=utc_now() - timedelta(hours=1),
        )
        db_session.add(expired)
        db_session.flush()

        assert expired.id not in {item.id for item in _inbox(db_session, admin_user)}


@pytest.mark.integration
class TestReadArchive:
    def test_mark_read_sets_both_timestamps_and_is_idempotent(
        self, db_session, admin_user
    ):
        message = Message(
            category=MessageCategory.announcement,
            body=TextBody(text="notice"),
        )
        db_session.add(message)
        db_session.flush()

        assert _unread_count(db_session, admin_user) == 1

        _mark_read(db_session, message_id=message.id, user_id=admin_user.id)
        rows = _receipt_rows(db_session, message.id)
        assert len(rows) == 1
        first_read = rows[0].read_at
        assert first_read is not None
        # Marking read also records seen (so a future seen/read split has data).
        assert rows[0].seen_at is not None
        assert _unread_count(db_session, admin_user) == 0

        _mark_read(db_session, message_id=message.id, user_id=admin_user.id)
        db_session.expire_all()
        rows = _receipt_rows(db_session, message.id)
        assert len(rows) == 1
        assert rows[0].read_at == first_read

    def test_mark_all_read_creates_receipts_for_untouched_broadcasts(
        self, db_session, admin_user
    ):
        first_global = Message(
            category=MessageCategory.announcement,
            body=TextBody(text="one"),
        )
        second_global = Message(
            category=MessageCategory.announcement,
            body=TextBody(text="two"),
        )
        direct = Message(
            category=MessageCategory.direct,
            body=TextBody(text="three"),
            recipient_id=admin_user.id,
        )
        db_session.add_all([first_global, second_global, direct])
        db_session.flush()

        _mark_all_read(db_session, admin_user)
        db_session.expire_all()

        read_message_ids = {
            row.message_id
            for row in db_session.scalars(
                select(MessageReceipt).where(
                    MessageReceipt.user_id == admin_user.id,
                    MessageReceipt.read_at.is_not(None),
                )
            ).all()
        }
        assert {first_global.id, second_global.id, direct.id} <= read_message_ids
        assert _unread_count(db_session, admin_user) == 0

    def test_archive_hides_then_unarchive_restores(self, db_session, admin_user):
        message = Message(
            category=MessageCategory.announcement,
            body=TextBody(text="archive me"),
        )
        db_session.add(message)
        db_session.flush()

        _archive(db_session, message_id=message.id, user_id=admin_user.id)
        db_session.expire_all()
        assert message.id not in {item.id for item in _inbox(db_session, admin_user)}

        # Unarchive: clear archived_at (no-op safe even if no row existed).
        receipt = db_session.scalars(
            select(MessageReceipt).where(
                MessageReceipt.message_id == message.id,
                MessageReceipt.user_id == admin_user.id,
            )
        ).one()
        receipt.archived_at = None
        db_session.flush()
        db_session.expire_all()
        assert message.id in {item.id for item in _inbox(db_session, admin_user)}


@pytest.mark.integration
class TestChangeLogExclusion:
    """Messages must never leak bodies or participant ids into ``change_log``."""

    def test_message_lifecycle_writes_no_change_log_rows(
        self, db_session, admin_user, editor_user
    ):
        message = Message(
            category=MessageCategory.direct,
            body=TextBody(text="private note"),
            sender_id=editor_user.id,
            recipient_id=admin_user.id,
        )
        db_session.add(message)
        db_session.flush()

        # Timestamps still applied by the audit hook despite the exclusion.
        assert message.created_at is not None
        assert message.updated_at is not None

        # Update and soft-delete paths.
        message.body = TextBody(text="edited private note")
        db_session.flush()
        message.deleted_at = utc_now()
        db_session.flush()

        rows = db_session.scalars(
            select(ChangeLog).where(ChangeLog.entity_type == "messages")
        ).all()
        assert list(rows) == []


@pytest.mark.integration
class TestConstraints:
    def test_duplicate_receipt_violates_unique(self, db_session, admin_user):
        message = Message(
            category=MessageCategory.announcement,
            body=TextBody(text="dup"),
        )
        db_session.add(message)
        db_session.flush()

        db_session.add(MessageReceipt(message_id=message.id, user_id=admin_user.id))
        db_session.flush()

        with pytest.raises(IntegrityError):
            with db_session.begin_nested():
                db_session.add(
                    MessageReceipt(message_id=message.id, user_id=admin_user.id)
                )
                db_session.flush()

    def test_related_entity_requires_both_or_neither(self, db_session):
        message = Message(
            category=MessageCategory.pin_rejection,
            body=PinRejectionBody(reason="dupe"),
            related_entity_type=EntityType.pin,
        )
        with pytest.raises(IntegrityError):
            with db_session.begin_nested():
                db_session.add(message)
                db_session.flush()

    def test_related_entity_both_set_is_allowed(self, db_session):
        message = Message(
            category=MessageCategory.pin_rejection,
            body=PinRejectionBody(reason="dupe", pin_id=7),
            related_entity_type=EntityType.pin,
            related_entity_id=7,
        )
        db_session.add(message)
        db_session.flush()
        assert message.id is not None
