"""Typed query helpers for user pin lists (favorites / collection / wants / trades).

Used by the user profile page and the dedicated full-list pages so the query
shapes only live in one place.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from pindb.database.joins import user_favorite_pins
from pindb.database.pin import Pin
from pindb.database.user_owned_pin import UserOwnedPin
from pindb.database.user_wanted_pin import UserWantedPin


# ---------------------------------------------------------------------------
# Favorites
# ---------------------------------------------------------------------------


def count_favorites(*, session: Session, user_id: int) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(user_favorite_pins)
            .where(user_favorite_pins.c.user_id == user_id)
        )
        or 0
    )


def get_favorite_pins(
    *,
    session: Session,
    user_id: int,
    limit: int,
    offset: int = 0,
    eager_pin_relationships: bool = False,
) -> list[Pin]:
    statement = (
        select(Pin)
        .join(user_favorite_pins, Pin.id == user_favorite_pins.c.pin_id)
        .where(user_favorite_pins.c.user_id == user_id)
        .order_by(Pin.name)
        .limit(limit)
        .offset(offset)
    )
    if eager_pin_relationships:
        statement = statement.options(
            selectinload(Pin.shops),
            selectinload(Pin.artists),
        )
    return list(session.scalars(statement).all())


# ---------------------------------------------------------------------------
# Collection / Trades (UserOwnedPin)
# ---------------------------------------------------------------------------


def count_owned(*, session: Session, user_id: int, tradeable_only: bool = False) -> int:
    statement = select(func.count(func.distinct(UserOwnedPin.pin_id))).where(
        UserOwnedPin.user_id == user_id
    )
    if tradeable_only:
        statement = statement.where(UserOwnedPin.tradeable_quantity > 0)
    return session.scalar(statement) or 0


def get_owned_entries(
    *,
    session: Session,
    user_id: int,
    limit: int,
    offset: int = 0,
    tradeable_only: bool = False,
    eager_pin_relationships: bool = False,
) -> list[UserOwnedPin]:
    """Two-phase fetch: pick distinct pin ids, then load grade rows for them.

    Keeps grade rows grouped by pin and avoids cartesian explosions.
    """
    pin_ids_statement = (
        select(UserOwnedPin.pin_id)
        .distinct()
        .where(UserOwnedPin.user_id == user_id)
        .order_by(UserOwnedPin.pin_id)
        .limit(limit)
        .offset(offset)
    )
    if tradeable_only:
        pin_ids_statement = pin_ids_statement.where(UserOwnedPin.tradeable_quantity > 0)

    pin_ids = list(session.scalars(pin_ids_statement))
    if not pin_ids:
        return []

    entries_statement = (
        select(UserOwnedPin)
        .where(
            UserOwnedPin.user_id == user_id,
            UserOwnedPin.pin_id.in_(pin_ids),
        )
        .order_by(UserOwnedPin.pin_id, UserOwnedPin.grade_id)
    )
    if tradeable_only:
        entries_statement = entries_statement.where(UserOwnedPin.tradeable_quantity > 0)

    pin_loader = selectinload(UserOwnedPin.pin)
    if eager_pin_relationships:
        pin_loader = pin_loader.options(
            selectinload(Pin.shops),
            selectinload(Pin.artists),
        )

    return list(
        session.scalars(
            entries_statement.options(pin_loader, selectinload(UserOwnedPin.grade))
        )
    )


# ---------------------------------------------------------------------------
# Wants (UserWantedPin)
# ---------------------------------------------------------------------------


def count_wanted(*, session: Session, user_id: int) -> int:
    return (
        session.scalar(
            select(func.count(func.distinct(UserWantedPin.pin_id))).where(
                UserWantedPin.user_id == user_id
            )
        )
        or 0
    )


def get_wanted_entries(
    *,
    session: Session,
    user_id: int,
    limit: int,
    offset: int = 0,
    eager_pin_relationships: bool = False,
) -> list[UserWantedPin]:
    pin_ids = list(
        session.scalars(
            select(UserWantedPin.pin_id)
            .distinct()
            .where(UserWantedPin.user_id == user_id)
            .order_by(UserWantedPin.pin_id)
            .limit(limit)
            .offset(offset)
        )
    )
    if not pin_ids:
        return []

    pin_loader = selectinload(UserWantedPin.pin)
    if eager_pin_relationships:
        pin_loader = pin_loader.options(
            selectinload(Pin.shops),
            selectinload(Pin.artists),
        )

    return list(
        session.scalars(
            select(UserWantedPin)
            .where(
                UserWantedPin.user_id == user_id,
                UserWantedPin.pin_id.in_(pin_ids),
            )
            .options(pin_loader, selectinload(UserWantedPin.grade))
            .order_by(UserWantedPin.pin_id, UserWantedPin.grade_id)
        )
    )
