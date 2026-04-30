"""Shared duplicate-name checks for HTMX create/edit form feedback."""

from enum import StrEnum

from fastapi.responses import HTMLResponse
from htpy import p
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from pindb.database import Artist, Pin, PinSet, Shop, Tag
from pindb.database.tag import normalize_tag_name


class NameCheckKind(StrEnum):
    """Entity kinds supported by the generic create/edit name check endpoint."""

    pin = "pin"
    shop = "shop"
    tag = "tag"
    artist = "artist"
    pin_set = "pin_set"


def normalized_name_key(name: str) -> str:
    """Return the canonical stored comparison key for a user-entered name."""
    return normalize_tag_name(name=name)


def duplicate_name_response(name: str) -> HTMLResponse:
    """Return an inline duplicate-name warning fragment."""
    display_name: str = name.strip()
    return HTMLResponse(
        content=str(
            p(
                class_="text-sm text-error-main underline decoration-error-main underline-offset-2"
            )[f"{display_name} already exists!"]
        )
    )


def empty_name_check_response() -> HTMLResponse:
    """Return an empty fragment so HTMX clears prior feedback."""
    return HTMLResponse(content="")


async def normalized_name_exists(
    *,
    session: AsyncSession,
    kind: NameCheckKind,
    normalized_name: str,
    exclude_id: int | None = None,
    owner_id: int | None = None,
    global_pin_sets: bool = False,
    include_pending: bool = False,
) -> bool:
    """Return whether a visible row already has the normalized name.

    Args:
        session: SQLAlchemy session with audit visibility criteria applied.
        kind: Entity kind to check.
        normalized_name: Canonical generated-column key.
        exclude_id: Existing row to ignore for edit forms.
        owner_id: Personal pin-set owner scope. Only used for ``pin_set``.
        global_pin_sets: Scope pin-set checks to global sets.
        include_pending: Bypass pending visibility filtering where ownership
            already scopes the query, such as personal set checks.

    Returns:
        ``True`` when a row exists in the requested scope.
    """
    statement: Select[tuple[int]]

    match kind:
        case NameCheckKind.pin:
            statement = select(Pin.id).where(Pin.normalized_name == normalized_name)
            if exclude_id is not None:
                statement = statement.where(Pin.id != exclude_id)
        case NameCheckKind.shop:
            statement = select(Shop.id).where(Shop.normalized_name == normalized_name)
            if exclude_id is not None:
                statement = statement.where(Shop.id != exclude_id)
        case NameCheckKind.tag:
            statement = select(Tag.id).where(Tag.normalized_name == normalized_name)
            if exclude_id is not None:
                statement = statement.where(Tag.id != exclude_id)
        case NameCheckKind.artist:
            statement = select(Artist.id).where(
                Artist.normalized_name == normalized_name
            )
            if exclude_id is not None:
                statement = statement.where(Artist.id != exclude_id)
        case NameCheckKind.pin_set:
            statement = select(PinSet.id).where(
                PinSet.normalized_name == normalized_name
            )
            if owner_id is not None:
                statement = statement.where(PinSet.owner_id == owner_id)
            elif global_pin_sets:
                statement = statement.where(PinSet.owner_id.is_(None))
            if exclude_id is not None:
                statement = statement.where(PinSet.id != exclude_id)

    statement = statement.limit(1)
    if include_pending:
        statement = statement.execution_options(include_pending=True)
    return (await session.scalar(statement=statement)) is not None
