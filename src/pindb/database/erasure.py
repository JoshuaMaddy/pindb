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

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from pindb.database.artist import Artist
from pindb.database.change_log import ChangeLog
from pindb.database.currency import Currency
from pindb.database.grade import Grade
from pindb.database.joins import (
    pin_set_memberships,
    pin_sets_links,
    user_favorite_pin_sets,
    user_favorite_pins,
)
from pindb.database.link import Link
from pindb.database.pending_edit import PendingEdit
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.session import UserSession
from pindb.database.shop import Shop
from pindb.database.tag import Tag
from pindb.database.user import User
from pindb.database.user_auth_provider import UserAuthProvider
from pindb.database.user_owned_pin import UserOwnedPin
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
)
_AUDIT_FIELDS = ("created_by_id", "updated_by_id", "deleted_by_id")

# PendingMixin adds approved_by_id / rejected_by_id on top of AuditMixin.
_PENDING_MODELS = (Artist, Shop, Tag, PinSet, Pin)
_PENDING_FIELDS = ("approved_by_id", "rejected_by_id")


def erase_user_account(session: Session, user_id: int) -> None:
    """Erase a user account and anonymise all audit references to it.

    Run inside a transactional session (``session_maker.begin()``). The
    function issues bulk UPDATE and DELETE statements:

    1. Every AuditMixin FK to this user is set to NULL.
    2. Every PendingMixin approved/rejected FK to this user is set to NULL.
    3. ChangeLog and PendingEdit FKs to this user are set to NULL.
    4. Personal PinSets owned by this user are hard-deleted along with
       their memberships, favorites-of, and link associations.
    5. Join-table rows (favorites), OAuth linkages, sessions, and
       per-user pin-list rows are deleted outright.
    6. The user row itself is deleted.
    """
    # 1. Anonymise AuditMixin FKs across every inheriting table.
    for model in _AUDIT_MODELS:
        for field in _AUDIT_FIELDS:
            col = getattr(model, field)
            session.execute(update(model).where(col == user_id).values({field: None}))

    # 2. Anonymise PendingMixin FKs.
    for model in _PENDING_MODELS:
        for field in _PENDING_FIELDS:
            col = getattr(model, field)
            session.execute(update(model).where(col == user_id).values({field: None}))

    # 3. Anonymise ChangeLog + PendingEdit (not AuditMixin).
    session.execute(
        update(ChangeLog)
        .where(ChangeLog.changed_by_id == user_id)
        .values(changed_by_id=None)
    )
    for field in ("created_by_id", "approved_by_id", "rejected_by_id"):
        col = getattr(PendingEdit, field)
        session.execute(update(PendingEdit).where(col == user_id).values({field: None}))

    # 4. Hard-delete personal PinSets owned by this user. Drop every
    #    join row that references them first to satisfy FK constraints.
    personal_set_ids = list(
        session.scalars(select(PinSet.id).where(PinSet.owner_id == user_id)).all()
    )
    if personal_set_ids:
        session.execute(
            delete(pin_set_memberships).where(
                pin_set_memberships.c.set_id.in_(personal_set_ids)
            )
        )
        session.execute(
            delete(pin_sets_links).where(
                pin_sets_links.c.pin_set_id.in_(personal_set_ids)
            )
        )
        session.execute(
            delete(user_favorite_pin_sets).where(
                user_favorite_pin_sets.c.pin_set_id.in_(personal_set_ids)
            )
        )
        session.execute(delete(PinSet).where(PinSet.id.in_(personal_set_ids)))

    # 5. Drop user-owned data.
    session.execute(
        delete(user_favorite_pins).where(user_favorite_pins.c.user_id == user_id)
    )
    session.execute(
        delete(user_favorite_pin_sets).where(
            user_favorite_pin_sets.c.user_id == user_id
        )
    )
    session.execute(delete(UserAuthProvider).where(UserAuthProvider.user_id == user_id))
    session.execute(delete(UserSession).where(UserSession.user_id == user_id))
    session.execute(delete(UserOwnedPin).where(UserOwnedPin.user_id == user_id))
    session.execute(delete(UserWantedPin).where(UserWantedPin.user_id == user_id))

    # 6. Delete the user row. All references above are gone, so no FK
    #    violation.
    session.execute(delete(User).where(User.id == user_id))
