"""GDPR-compliant account erasure.

Public API: ``erase_user_account(session, user_id)``.

The privacy policy promises that, on account deletion, audit-log
references to the user are anonymised. This module does exactly that.
Every column that references ``users.id`` is either set to NULL
(audit / authorship fields) or the row is removed entirely (user-owned
data such as sessions, OAuth links, favorites, owned/wanted pins).

Raw UPDATE / DELETE statements are used throughout so the ORM-level
audit events in ``audit_events.py`` do not write the old user_id
values into ``change_log.patch`` while we are trying to remove them.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from pindb.database.artist import Artist
from pindb.database.change_log import ChangeLog
from pindb.database.content_report import ContentReport, ReportTargetType
from pindb.database.currency import Currency
from pindb.database.grade import Grade
from pindb.database.joins import (
    display_image_pins,
    pin_set_memberships,
    pin_sets_links,
    user_favorite_pin_sets,
    user_favorite_pins,
)
from pindb.database.link import Link
from pindb.database.message import Message, MessageReceipt
from pindb.database.pending_edit import PendingEdit
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.session import UserSession
from pindb.database.shop import Shop
from pindb.database.tag import Tag
from pindb.database.user import User
from pindb.database.user_auth_provider import UserAuthProvider
from pindb.database.user_display import UserDisplay, UserDisplayImage
from pindb.database.user_owned_pin import UserOwnedPin
from pindb.database.user_stats import UserAchievement, UserStats
from pindb.database.user_wanted_pin import UserWantedPin

# Every model carrying AuditMixin has created_by_id / updated_by_id /
# deleted_by_id FKs to users.id.
_AUDIT_MODELS = (
    Artist,
    Shop,
    Tag,
    PinSet,
    Pin,
    Grade,
    Link,
    Currency,
    User,
    UserAuthProvider,
    UserOwnedPin,
    UserWantedPin,
    Message,
    UserDisplay,
    UserDisplayImage,
)
_AUDIT_FIELDS = ("created_by_id", "updated_by_id", "deleted_by_id")

# PendingMixin adds approved_by_id / rejected_by_id on top of AuditMixin.
_PENDING_MODELS = (Artist, Shop, Tag, PinSet, Pin)
_PENDING_FIELDS = ("approved_by_id", "rejected_by_id")


async def erase_user_account(session: AsyncSession, user_id: int) -> list[UUID]:
    """Erase a user account and anonymise all audit references to it.

    Run inside a transactional session (``async_session_maker.begin()``). The
    function issues bulk UPDATE and DELETE statements:

    1. Every AuditMixin FK to this user is set to NULL.
    2. Every PendingMixin approved/rejected FK to this user is set to NULL.
    3. ChangeLog and PendingEdit FKs to this user are set to NULL.
    4. Personal PinSets owned by this user are hard-deleted along with
       their memberships, favorites-of, and link associations.
    5. Messages addressed to the user are hard-deleted (nobody else can
       see them), messages they sent are anonymised (``sender_id`` NULL),
       and their message receipts are removed.
    6. The display page, its photos, and their pin taggings are hard-deleted.
       Reports *about* those photos go with them; reports *filed by* the user
       survive, anonymised — an abuse report should outlive its reporter.
    7. Join-table rows (favorites), OAuth linkages, sessions, and
       per-user pin-list rows are deleted outright.
    8. The user row itself is deleted.

    Returns:
        list[UUID]: Image guids whose stored bytes must now be deleted. Display
            photos are pictures of someone's home, so erasure has to reach the
            storage backend too — but blob deletion is irreversible and must not
            happen inside the transaction, where a rollback would leave rows
            pointing at bytes that no longer exist. Callers pass these to
            ``file_handler.delete_image`` **after** the session commits, the same
            ordering the Meili and stats sync rules use.
    """
    # 1. Anonymise AuditMixin FKs across every inheriting table.
    for model in _AUDIT_MODELS:
        for field in _AUDIT_FIELDS:
            col = getattr(model, field)
            await session.execute(
                update(model).where(col == user_id).values(**{field: None})
            )

    # 2. Anonymise PendingMixin FKs.
    for model in _PENDING_MODELS:
        for field in _PENDING_FIELDS:
            col = getattr(model, field)
            await session.execute(
                update(model).where(col == user_id).values(**{field: None})
            )

    # 3. Anonymise ChangeLog + PendingEdit (not AuditMixin).
    await session.execute(
        update(ChangeLog)
        .where(ChangeLog.changed_by_id == user_id)
        .values(changed_by_id=None)
    )
    for field in ("created_by_id", "approved_by_id", "rejected_by_id"):
        col = getattr(PendingEdit, field)
        await session.execute(
            update(PendingEdit).where(col == user_id).values(**{field: None})
        )

    # 4. Hard-delete personal PinSets owned by this user. Drop every
    #    join row that references them first to satisfy FK constraints.
    personal_set_ids = list(
        (
            await session.scalars(select(PinSet.id).where(PinSet.owner_id == user_id))
        ).all()
    )
    if personal_set_ids:
        await session.execute(
            delete(pin_set_memberships).where(
                pin_set_memberships.c.set_id.in_(personal_set_ids)
            )
        )
        await session.execute(
            delete(pin_sets_links).where(
                pin_sets_links.c.pin_set_id.in_(personal_set_ids)
            )
        )
        await session.execute(
            delete(user_favorite_pin_sets).where(
                user_favorite_pin_sets.c.pin_set_id.in_(personal_set_ids)
            )
        )
        await session.execute(delete(PinSet).where(PinSet.id.in_(personal_set_ids)))

    # 5. Messages. Delete the user's inbox outright — a direct message to
    #    them is visible to nobody else, and its body may be personal data.
    #    Other users' receipts on those rows cascade at the DB level
    #    (message_id ondelete CASCADE); replies pointing at deleted rows get
    #    parent_id SET NULL. Sent messages survive anonymised, like other
    #    contributed content.
    await session.execute(delete(Message).where(Message.recipient_id == user_id))
    await session.execute(
        update(Message).where(Message.sender_id == user_id).values(sender_id=None)
    )
    await session.execute(
        delete(MessageReceipt).where(MessageReceipt.user_id == user_id)
    )

    # 6. The display page and its photos. Unlike pin art — which belongs to
    #    catalog pins that survive the user, anonymised — these are personal
    #    photographs that nothing else references once the account is gone.
    #    Bulk statements bypass the ORM cascade, so each level is deleted by
    #    hand, deepest first.
    orphaned_image_guids: list[UUID] = []
    display_ids = list(
        (
            await session.scalars(
                select(UserDisplay.id).where(UserDisplay.user_id == user_id)
            )
        ).all()
    )
    if display_ids:
        image_rows = (
            await session.execute(
                select(UserDisplayImage.id, UserDisplayImage.image_guid).where(
                    UserDisplayImage.display_id.in_(display_ids)
                )
            )
        ).all()
        image_ids = [image_id for image_id, _ in image_rows]
        orphaned_image_guids = [guid for _, guid in image_rows]
        if image_ids:
            await session.execute(
                delete(display_image_pins).where(
                    display_image_pins.c.display_image_id.in_(image_ids)
                )
            )
            # ContentReport points at its target with a plain (type, id) pair and
            # no foreign key, so nothing cascades and no FK check will ever catch
            # this. Reports filed *against* these photos have to go with them or
            # they dangle at rows that no longer exist.
            await session.execute(
                delete(ContentReport).where(
                    ContentReport.target_type == ReportTargetType.display_image,
                    ContentReport.target_id.in_(image_ids),
                )
            )
            await session.execute(
                delete(UserDisplayImage).where(UserDisplayImage.id.in_(image_ids))
            )
        await session.execute(
            delete(UserDisplay).where(UserDisplay.id.in_(display_ids))
        )

    # Reports the user *filed* survive, anonymised: an abuse report is about
    # someone else's content and an admin may still need to act on it. This is
    # why reporter_id is nullable.
    await session.execute(
        update(ContentReport)
        .where(ContentReport.reporter_id == user_id)
        .values(reporter_id=None)
    )
    await session.execute(
        update(ContentReport)
        .where(ContentReport.resolved_by_id == user_id)
        .values(resolved_by_id=None)
    )

    # 7. Drop the rest of the user-owned data.
    await session.execute(
        delete(user_favorite_pins).where(user_favorite_pins.c.user_id == user_id)
    )
    await session.execute(
        delete(user_favorite_pin_sets).where(
            user_favorite_pin_sets.c.user_id == user_id
        )
    )
    await session.execute(
        delete(UserAuthProvider).where(UserAuthProvider.user_id == user_id)
    )
    await session.execute(delete(UserSession).where(UserSession.user_id == user_id))
    await session.execute(delete(UserOwnedPin).where(UserOwnedPin.user_id == user_id))
    await session.execute(delete(UserWantedPin).where(UserWantedPin.user_id == user_id))
    await session.execute(delete(UserStats).where(UserStats.user_id == user_id))
    await session.execute(
        delete(UserAchievement).where(UserAchievement.user_id == user_id)
    )

    # 8. Delete the user row. All references above are gone, so no FK
    #    violation.
    await session.execute(delete(User).where(User.id == user_id))

    return orphaned_image_guids
