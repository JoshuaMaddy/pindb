"""Messages and per-user receipts: body typing, lazy broadcast inbox, audience
scoping, expiry, seen/read/archive upserts, and table constraints.

Receipts are created lazily, so the query helpers here mirror the intended route
logic: reads LEFT JOIN receipts for the current user and treat a missing row as
"unseen, unread, not archived"; writes UPSERT the receipt.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy import and_, func, literal, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
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
from pindb.database.user import User
from pindb.models.message_body import (
    ContributionBody,
    MessageBodyAdapter,
    PinRejectionBody,
    TextBody,
)
from pindb.utils import utc_now

# --- Query helpers (stand-ins for the future inbox routes) ------------------


def _broadcast_audiences(user: User) -> list[MessageAudience]:
    """Broadcast audiences the *user* is allowed to receive."""
    audiences: list[MessageAudience] = [MessageAudience.all]
    if user.is_editor or user.is_admin:
        audiences.append(MessageAudience.editors)
    if user.is_admin:
        audiences.append(MessageAudience.admins)
    return audiences


def _visible_clause(user: User):
    """Direct-to-user OR an in-audience, unexpired broadcast."""
    now = utc_now()
    return and_(
        or_(
            Message.recipient_id == user.id,
            and_(
                Message.recipient_id.is_(None),
                Message.audience.in_(_broadcast_audiences(user)),
            ),
        ),
        or_(
            Message.expires_at.is_(None),
            Message.expires_at > now,
        ),
    )


def _inbox(session: Session, user: User) -> list[Message]:
    """Non-archived visible messages, newest first."""
    statement = (
        select(Message)
        .outerjoin(
            MessageReceipt,
            and_(
                MessageReceipt.message_id == Message.id,
                MessageReceipt.user_id == user.id,
            ),
        )
        .where(
            _visible_clause(user),
            MessageReceipt.archived_at.is_(None),
        )
        .order_by(Message.created_at.desc())
    )
    return list(session.scalars(statement).all())


def _unread_count(session: Session, user: User) -> int:
    """Count of visible, unseen, non-archived messages."""
    statement = (
        select(func.count())
        .select_from(Message)
        .outerjoin(
            MessageReceipt,
            and_(
                MessageReceipt.message_id == Message.id,
                MessageReceipt.user_id == user.id,
            ),
        )
        .where(
            _visible_clause(user),
            MessageReceipt.seen_at.is_(None),
            MessageReceipt.archived_at.is_(None),
        )
    )
    return session.scalar(statement) or 0


def _mark_seen(session: Session, *, message_id: int, user_id: int) -> None:
    """Idempotently record that *user* has seen *message* (first-seen preserved)."""
    now = utc_now()
    statement = (
        pg_insert(MessageReceipt)
        .values(message_id=message_id, user_id=user_id, seen_at=now)
        .on_conflict_do_update(
            index_elements=["message_id", "user_id"],
            set_={"seen_at": func.coalesce(MessageReceipt.seen_at, now)},
        )
    )
    session.execute(statement)


def _mark_all_seen(session: Session, user: User) -> None:
    """Mark every visible unseen message seen, creating receipts as needed."""
    now = utc_now()
    selectable = (
        select(Message.id, literal(user.id), literal(now))
        .outerjoin(
            MessageReceipt,
            and_(
                MessageReceipt.message_id == Message.id,
                MessageReceipt.user_id == user.id,
            ),
        )
        .where(
            _visible_clause(user),
            MessageReceipt.seen_at.is_(None),
        )
    )
    statement = (
        pg_insert(MessageReceipt)
        .from_select(["message_id", "user_id", "seen_at"], selectable)
        .on_conflict_do_update(
            index_elements=["message_id", "user_id"],
            set_={"seen_at": func.coalesce(MessageReceipt.seen_at, now)},
        )
    )
    session.execute(statement)


def _archive(session: Session, *, message_id: int, user_id: int) -> None:
    """Archive a message for a user (creates the receipt on first archive)."""
    now = utc_now()
    statement = (
        pg_insert(MessageReceipt)
        .values(message_id=message_id, user_id=user_id, archived_at=now)
        .on_conflict_do_update(
            index_elements=["message_id", "user_id"],
            set_={"archived_at": now},
        )
    )
    session.execute(statement)


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

    def test_unknown_body_type_fails_validation(self):
        with pytest.raises(ValidationError):
            MessageBodyAdapter.validate_python({"type": "not_a_real_kind"})


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
class TestSeenReadArchive:
    def test_mark_seen_is_idempotent_and_preserves_first_seen(
        self, db_session, admin_user
    ):
        message = Message(
            category=MessageCategory.announcement,
            body=TextBody(text="notice"),
        )
        db_session.add(message)
        db_session.flush()

        _mark_seen(db_session, message_id=message.id, user_id=admin_user.id)
        rows = _receipt_rows(db_session, message.id)
        assert len(rows) == 1
        first_seen = rows[0].seen_at
        assert first_seen is not None
        assert _unread_count(db_session, admin_user) == 0

        _mark_seen(db_session, message_id=message.id, user_id=admin_user.id)
        db_session.expire_all()
        rows = _receipt_rows(db_session, message.id)
        assert len(rows) == 1
        assert rows[0].seen_at == first_seen

    def test_mark_all_seen_creates_receipts_for_untouched_broadcasts(
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

        _mark_all_seen(db_session, admin_user)
        db_session.expire_all()

        seen_message_ids = {
            row.message_id
            for row in db_session.scalars(
                select(MessageReceipt).where(
                    MessageReceipt.user_id == admin_user.id,
                    MessageReceipt.seen_at.is_not(None),
                )
            ).all()
        }
        assert {first_global.id, second_global.id, direct.id} <= seen_message_ids
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
