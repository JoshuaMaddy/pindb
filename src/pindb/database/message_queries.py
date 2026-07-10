"""Canonical query logic for the messages inbox, as un-executed statement builders.

Every helper returns a SQLAlchemy statement without executing it, so the sync
integration tests (``Session.execute``) and the async routes/middleware
(``AsyncSession.execute``) share one source of truth. Receipts are created
lazily, so reads LEFT JOIN ``MessageReceipt`` for the current user and treat a
missing row as "unseen, unread, not archived"; writes UPSERT the receipt.

Unread is keyed on ``read_at`` (the single read state surfaced in the UI). Read
upserts set both ``read_at`` and ``seen_at`` via ``coalesce`` so ``seen_at``
stays meaningful for a possible future seen-vs-read split at zero extra cost.
"""

from __future__ import annotations

from sqlalchemy import Select, and_, func, literal, or_, select
from sqlalchemy.dialects.postgresql import Insert as PGInsert
from sqlalchemy.dialects.postgresql import insert as pg_insert

from pindb.database.message import Message, MessageAudience, MessageReceipt
from pindb.database.user import User
from pindb.utils import utc_now


def broadcast_audiences(user: User) -> list[MessageAudience]:
    """Broadcast audiences *user* is allowed to receive, given their role."""
    audiences: list[MessageAudience] = [MessageAudience.all]
    if user.is_editor or user.is_admin:
        audiences.append(MessageAudience.editors)
    if user.is_admin:
        audiences.append(MessageAudience.admins)
    return audiences


def visible_clause(user: User):
    """Direct-to-user OR an in-audience, unexpired broadcast."""
    now = utc_now()
    return and_(
        Message.deleted_at.is_(None),
        or_(
            Message.recipient_id == user.id,
            and_(
                Message.recipient_id.is_(None),
                Message.audience.in_(broadcast_audiences(user)),
            ),
        ),
        or_(
            Message.expires_at.is_(None),
            Message.expires_at > now,
        ),
    )


def _receipt_join(user: User):
    """LEFT JOIN condition matching *user*'s receipt for each message."""
    return and_(
        MessageReceipt.message_id == Message.id,
        MessageReceipt.user_id == user.id,
    )


def inbox_statement(user: User, *, limit: int, offset: int) -> Select[tuple[Message]]:
    """Visible, non-archived messages, newest first, paginated."""
    return (
        select(Message)
        .outerjoin(MessageReceipt, _receipt_join(user))
        .where(visible_clause(user), MessageReceipt.archived_at.is_(None))
        .order_by(Message.created_at.desc())
        .limit(limit)
        .offset(offset)
    )


def archived_statement(
    user: User, *, limit: int, offset: int
) -> Select[tuple[Message]]:
    """Visible messages the user has archived, newest first, paginated."""
    return (
        select(Message)
        .join(MessageReceipt, _receipt_join(user))
        .where(visible_clause(user), MessageReceipt.archived_at.is_not(None))
        .order_by(Message.created_at.desc())
        .limit(limit)
        .offset(offset)
    )


def inbox_count_statement(user: User) -> Select[tuple[int]]:
    """Total count of visible, non-archived messages (for pagination)."""
    return (
        select(func.count())
        .select_from(Message)
        .outerjoin(MessageReceipt, _receipt_join(user))
        .where(visible_clause(user), MessageReceipt.archived_at.is_(None))
    )


def archived_count_statement(user: User) -> Select[tuple[int]]:
    """Total count of archived messages (for pagination)."""
    return (
        select(func.count())
        .select_from(Message)
        .join(MessageReceipt, _receipt_join(user))
        .where(visible_clause(user), MessageReceipt.archived_at.is_not(None))
    )


def unread_count_statement(user: User) -> Select[tuple[int]]:
    """Count of visible, unread (``read_at IS NULL``), non-archived messages."""
    return (
        select(func.count())
        .select_from(Message)
        .outerjoin(MessageReceipt, _receipt_join(user))
        .where(
            visible_clause(user),
            MessageReceipt.read_at.is_(None),
            MessageReceipt.archived_at.is_(None),
        )
    )


def mark_read_statement(*, message_id: int, user_id: int) -> PGInsert:
    """Idempotently mark one message read (first-read timestamps preserved)."""
    now = utc_now()
    return (
        pg_insert(MessageReceipt)
        .values(message_id=message_id, user_id=user_id, seen_at=now, read_at=now)
        .on_conflict_do_update(
            index_elements=["message_id", "user_id"],
            set_={
                "seen_at": func.coalesce(MessageReceipt.seen_at, now),
                "read_at": func.coalesce(MessageReceipt.read_at, now),
            },
        )
    )


def mark_all_read_statement(user: User) -> PGInsert:
    """Mark every visible unread message read, creating receipts as needed."""
    now = utc_now()
    selectable = (
        select(Message.id, literal(user.id), literal(now), literal(now))
        .outerjoin(MessageReceipt, _receipt_join(user))
        .where(
            visible_clause(user),
            MessageReceipt.read_at.is_(None),
            MessageReceipt.archived_at.is_(None),
        )
    )
    return (
        pg_insert(MessageReceipt)
        .from_select(["message_id", "user_id", "seen_at", "read_at"], selectable)
        .on_conflict_do_update(
            index_elements=["message_id", "user_id"],
            set_={
                "seen_at": func.coalesce(MessageReceipt.seen_at, now),
                "read_at": func.coalesce(MessageReceipt.read_at, now),
            },
        )
    )


def archive_statement(*, message_id: int, user_id: int) -> PGInsert:
    """Archive a message for a user (creates the receipt on first archive)."""
    now = utc_now()
    return (
        pg_insert(MessageReceipt)
        .values(message_id=message_id, user_id=user_id, archived_at=now)
        .on_conflict_do_update(
            index_elements=["message_id", "user_id"],
            set_={"archived_at": now},
        )
    )


def unarchive_statement(*, message_id: int, user_id: int) -> PGInsert:
    """Clear a message's archived state for a user (no-op if no receipt existed)."""
    return (
        pg_insert(MessageReceipt)
        .values(message_id=message_id, user_id=user_id, archived_at=None)
        .on_conflict_do_update(
            index_elements=["message_id", "user_id"],
            set_={"archived_at": None},
        )
    )
