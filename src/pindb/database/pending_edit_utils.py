"""Snapshot/patch/apply helpers for the PendingEdit workflow.

A snapshot is a JSON-safe dict of an entity's editable fields. A patch is
a dict of {field: {"old": ..., "new": ...}}. Pending edits stack: each edit's
patch is relative to the effective state of the chain below it. Approving a
chain means computing the effective snapshot and writing it to the canonical
row.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes

from pindb.database.artist import Artist
from pindb.database.currency import Currency
from pindb.database.grade import Grade
from pindb.database.link import Link
from pindb.database.pending_edit import PendingEdit
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.pin_writes import sync_symmetric_pin_links, upsert_grades
from pindb.database.shop import Shop
from pindb.database.tag import (
    Tag,
    TagAlias,
    TagCategory,
    _cascade_remove_implied,
    apply_pin_tags,
    cascade_new_implications_to_pins,
    replace_tag_aliases,
    resolve_implications,
)
from pindb.models.acquisition_type import AcquisitionType
from pindb.models.funding_type import FundingType

# ---------------------------------------------------------------------------
# Snapshot construction
# ---------------------------------------------------------------------------


def snapshot_pin(pin: Pin) -> dict[str, Any]:
    """Flatten a ``Pin`` graph into JSON-safe primitives for pending-edit diffs."""
    return {
        "name": pin.name,
        "acquisition_type": pin.acquisition_type.value,
        "limited_edition": pin.limited_edition,
        "number_produced": pin.number_produced,
        "release_date": pin.release_date.isoformat() if pin.release_date else None,
        "end_date": pin.end_date.isoformat() if pin.end_date else None,
        "funding_type": pin.funding_type.value if pin.funding_type else None,
        "posts": pin.posts,
        "width": pin.width,
        "height": pin.height,
        "description": pin.description,
        "sku": pin.sku,
        "currency_id": pin.currency_id,
        "front_image_guid": str(pin.front_image_guid),
        "back_image_guid": str(pin.back_image_guid) if pin.back_image_guid else None,
        "shop_ids": sorted(shop.id for shop in pin.shops),
        "tag_ids": sorted(tag.id for tag in pin.explicit_tags),
        "artist_ids": sorted(artist.id for artist in pin.artists),
        "pin_set_ids": sorted(pin_set.id for pin_set in pin.sets),
        "variant_pin_ids": sorted(variant.id for variant in pin.variants),
        "unauthorized_copy_pin_ids": sorted(
            copy.id for copy in pin.unauthorized_copies
        ),
        "links": sorted(link.path for link in pin.links),
        "grades": sorted(
            [{"name": grade.name, "price": grade.price} for grade in pin.grades],
            key=lambda grade: grade["name"],
        ),
    }


def snapshot_artist(artist: Artist) -> dict[str, Any]:
    """Snapshot editable ``Artist`` columns and link URLs."""
    return {
        "name": artist.name,
        "description": artist.description,
        "active": artist.active,
        "links": sorted(link.path for link in artist.links),
    }


def snapshot_shop(shop: Shop) -> dict[str, Any]:
    """Snapshot editable ``Shop`` columns and link URLs."""
    return {
        "name": shop.name,
        "description": shop.description,
        "active": shop.active,
        "links": sorted(link.path for link in shop.links),
    }


def snapshot_tag(tag: Tag) -> dict[str, Any]:
    """Snapshot ``Tag`` fields, implication ids, and alias strings."""
    return {
        "name": tag.name,
        "description": tag.description,
        "category": tag.category.value,
        "implication_ids": sorted(implied_tag.id for implied_tag in tag.implications),
        "aliases": sorted(tag_alias.alias for tag_alias in tag.aliases),
    }


def snapshot_entity(entity: Pin | Artist | Shop | Tag) -> dict[str, Any]:
    """Dispatch to entity-specific snapshot helpers."""
    if isinstance(entity, Pin):
        return snapshot_pin(entity)
    if isinstance(entity, Artist):
        return snapshot_artist(entity)
    if isinstance(entity, Shop):
        return snapshot_shop(entity)
    if isinstance(entity, Tag):
        return snapshot_tag(entity)
    raise TypeError(f"No snapshot defined for {type(entity).__name__}")


# ---------------------------------------------------------------------------
# Patch compute / apply
# ---------------------------------------------------------------------------


def compute_patch(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Build a field-wise ``{key: {old, new}}`` diff between two snapshots."""
    patch: dict[str, Any] = {}
    for key in set(old) | set(new):
        old_val = old.get(key)
        new_val = new.get(key)
        if old_val != new_val:
            patch[key] = {"old": old_val, "new": new_val}
    return patch


def apply_patch(snapshot: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Return *snapshot* with each patch field replaced by its ``new`` value."""
    result: dict[str, Any] = dict(snapshot)
    for key, change in patch.items():
        result[key] = change["new"]
    return result


# ---------------------------------------------------------------------------
# Chain queries
# ---------------------------------------------------------------------------


async def get_edit_chain(
    session: AsyncSession, entity_type: str, entity_id: int
) -> list[PendingEdit]:
    """Unapproved, unrejected pending edits for an entity, oldest first."""
    return list(
        (
            await session.scalars(
                select(PendingEdit)
                .where(
                    PendingEdit.entity_type == entity_type,
                    PendingEdit.entity_id == entity_id,
                    PendingEdit.approved_at.is_(None),
                    PendingEdit.rejected_at.is_(None),
                )
                .order_by(PendingEdit.created_at.asc(), PendingEdit.id.asc())
            )
        ).all()
    )


async def get_head_edit(
    session: AsyncSession, entity_type: str, entity_id: int
) -> PendingEdit | None:
    """Most recent unapproved edit for an entity, or None."""
    return await session.scalar(
        select(PendingEdit)
        .where(
            PendingEdit.entity_type == entity_type,
            PendingEdit.entity_id == entity_id,
            PendingEdit.approved_at.is_(None),
            PendingEdit.rejected_at.is_(None),
        )
        .order_by(PendingEdit.created_at.desc(), PendingEdit.id.desc())
        .limit(1)
    )


def get_effective_snapshot(
    entity: Pin | Artist | Shop | Tag, chain: Sequence[PendingEdit]
) -> dict[str, Any]:
    snapshot = snapshot_entity(entity)
    for edit in chain:
        snapshot = apply_patch(snapshot, edit.patch)
    return snapshot


async def has_pending_edits(
    session: AsyncSession, entity_type: str, entity_id: int
) -> bool:
    """Return whether any unapproved ``PendingEdit`` exists for the entity."""
    return await get_head_edit(session, entity_type, entity_id) is not None


async def maybe_apply_pending_view(
    *,
    session: AsyncSession,
    entity: Pin | Artist | Shop | Tag,
    entity_table: str,
    current_user: object,
    version: str | None,
) -> tuple[bool, bool]:
    """Returns ``(pending_chain_exists, viewing_pending)``.

    If the viewer is allowed to see pending edits *and* requested
    ``?version=pending``, mutates ``entity`` in-memory to reflect the pending
    chain. The mutation happens inside ``session.no_autoflush``.
    """
    can_see_pending = current_user is not None and (
        getattr(current_user, "is_editor", False)
        or getattr(current_user, "is_admin", False)
    )
    viewing_pending = version == "pending" and can_see_pending

    pending_chain_exists = can_see_pending and await has_pending_edits(
        session, entity_table, entity.id
    )

    if viewing_pending and pending_chain_exists:
        chain = await get_edit_chain(session, entity_table, entity.id)
        effective = get_effective_snapshot(entity, chain)
        with session.no_autoflush:
            await apply_snapshot_in_memory(entity, effective, session)

    return pending_chain_exists, viewing_pending


# ---------------------------------------------------------------------------
# In-memory apply (for form pre-population / pending view rendering)
# ---------------------------------------------------------------------------


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


async def apply_snapshot_in_memory(
    entity: Pin | Artist | Shop | Tag,
    snapshot: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Mutate an ORM entity in-memory to reflect a snapshot.

    Must be called inside session.no_autoflush to avoid accidental writes.
    Creates transient Link / Grade / TagAlias objects for display only;
    they should not be flushed.
    """
    if isinstance(entity, Pin):
        await _apply_pin_snapshot_in_memory(entity, snapshot, session)
    elif isinstance(entity, Artist):
        _apply_artist_snapshot_in_memory(entity, snapshot)
    elif isinstance(entity, Shop):
        _apply_shop_snapshot_in_memory(entity, snapshot)
    elif isinstance(entity, Tag):
        await _apply_tag_snapshot_in_memory(entity, snapshot, session)
    else:
        raise TypeError(f"No in-memory apply for {type(entity).__name__}")


async def _apply_pin_snapshot_in_memory(
    pin: Pin, snapshot: dict[str, Any], session: AsyncSession
) -> None:
    pin.name = snapshot["name"]
    pin.acquisition_type = AcquisitionType(snapshot["acquisition_type"])
    pin.limited_edition = snapshot["limited_edition"]
    pin.number_produced = snapshot["number_produced"]
    pin.release_date = _parse_date(snapshot["release_date"])
    pin.end_date = _parse_date(snapshot["end_date"])
    pin.funding_type = (
        FundingType(snapshot["funding_type"]) if snapshot["funding_type"] else None
    )
    pin.posts = snapshot["posts"]
    pin.width = snapshot["width"]
    pin.height = snapshot["height"]
    pin.description = snapshot["description"]
    pin.sku = snapshot["sku"]

    currency_id: int = snapshot["currency_id"]
    if pin.currency_id != currency_id:
        currency = await session.get(Currency, currency_id)
        if currency is not None:
            pin.currency = currency
            pin.currency_id = currency_id

    pin.front_image_guid = UUID(snapshot["front_image_guid"])
    pin.back_image_guid = (
        UUID(snapshot["back_image_guid"]) if snapshot["back_image_guid"] else None
    )

    pin.shops = set(
        (
            await session.scalars(
                select(Shop)
                .where(Shop.id.in_(snapshot["shop_ids"]))
                .execution_options(include_pending=True)
            )
        ).all()
    )
    explicit_tag_objs = set(
        (
            await session.scalars(
                select(Tag)
                .where(Tag.id.in_(snapshot["tag_ids"]))
                .execution_options(include_pending=True)
            )
        ).all()
    )
    resolved_tags = await resolve_implications(explicit_tag_objs, session)
    attributes.set_committed_value(pin, "explicit_tags", explicit_tag_objs)
    attributes.set_committed_value(pin, "tags", set(resolved_tags.keys()))
    pin.artists = set(
        (
            await session.scalars(
                select(Artist)
                .where(Artist.id.in_(snapshot["artist_ids"]))
                .execution_options(include_pending=True)
            )
        ).all()
    )
    if snapshot.get("pin_set_ids"):
        pin.sets = set(
            (
                await session.scalars(
                    select(PinSet)
                    .where(PinSet.id.in_(snapshot["pin_set_ids"]))
                    .execution_options(include_pending=True)
                )
            ).all()
        )
    else:
        pin.sets = set()

    variant_ids = snapshot.get("variant_pin_ids") or []
    copy_ids = snapshot.get("unauthorized_copy_pin_ids") or []
    pin_variants_set: set[Pin] = (
        set(
            (
                await session.scalars(
                    select(Pin)
                    .where(Pin.id.in_(variant_ids))
                    .execution_options(include_pending=True)
                )
            ).all()
        )
        if variant_ids
        else set()
    )
    pin_copies_set: set[Pin] = (
        set(
            (
                await session.scalars(
                    select(Pin)
                    .where(Pin.id.in_(copy_ids))
                    .execution_options(include_pending=True)
                )
            ).all()
        )
        if copy_ids
        else set()
    )
    attributes.set_committed_value(pin, "variants", pin_variants_set)
    attributes.set_committed_value(pin, "unauthorized_copies", pin_copies_set)

    pin.links = {Link(path=path) for path in snapshot["links"]}
    pin.grades = {
        Grade(name=grade["name"], price=grade.get("price"))
        for grade in snapshot["grades"]
    }


def _apply_artist_snapshot_in_memory(artist: Artist, snapshot: dict[str, Any]) -> None:
    artist.name = snapshot["name"]
    artist.description = snapshot["description"]
    artist.active = snapshot["active"]
    artist.links = {Link(path=path) for path in snapshot["links"]}


def _apply_shop_snapshot_in_memory(shop: Shop, snapshot: dict[str, Any]) -> None:
    shop.name = snapshot["name"]
    shop.description = snapshot["description"]
    shop.active = snapshot["active"]
    shop.links = {Link(path=path) for path in snapshot["links"]}


async def _apply_tag_snapshot_in_memory(
    tag: Tag, snapshot: dict[str, Any], session: AsyncSession
) -> None:
    tag.name = snapshot["name"]
    tag.description = snapshot["description"]
    tag.category = TagCategory(snapshot["category"])
    tag.implications = set(
        (
            await session.scalars(
                select(Tag)
                .where(Tag.id.in_(snapshot["implication_ids"]))
                .execution_options(include_pending=True)
            )
        ).all()
    )
    attributes.set_committed_value(
        tag,
        "aliases",
        [TagAlias(alias=alias_name) for alias_name in snapshot["aliases"]],
    )


# ---------------------------------------------------------------------------
# Approval apply (writes to DB)
# ---------------------------------------------------------------------------


async def apply_snapshot_to_entity(
    entity: Pin | Artist | Shop | Tag,
    snapshot: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Write snapshot values to the canonical entity as a real update.

    Used when an admin approves a pending edit chain. Handles link / grade
    replacement the same way the edit routes do.
    """
    if isinstance(entity, Pin):
        await _approve_pin_snapshot(entity, snapshot, session)
    elif isinstance(entity, Artist):
        await _approve_artist_snapshot(entity, snapshot, session)
    elif isinstance(entity, Shop):
        await _approve_shop_snapshot(entity, snapshot, session)
    elif isinstance(entity, Tag):
        await _approve_tag_snapshot(entity, snapshot, session)
    else:
        raise TypeError(f"No approval apply for {type(entity).__name__}")


async def _replace_links(
    entity: Pin | Artist | Shop, new_urls: list[str], session: AsyncSession
) -> None:
    for old_link in list(entity.links):
        await session.delete(old_link)
    entity.links = {Link(path=url) for url in new_urls}


async def _approve_pin_snapshot(
    pin: Pin, snapshot: dict[str, Any], session: AsyncSession
) -> None:
    pin.name = snapshot["name"]
    pin.acquisition_type = AcquisitionType(snapshot["acquisition_type"])
    pin.limited_edition = snapshot["limited_edition"]
    pin.number_produced = snapshot["number_produced"]
    pin.release_date = _parse_date(snapshot["release_date"])
    pin.end_date = _parse_date(snapshot["end_date"])
    pin.funding_type = (
        FundingType(snapshot["funding_type"]) if snapshot["funding_type"] else None
    )
    pin.posts = snapshot["posts"]
    pin.width = snapshot["width"]
    pin.height = snapshot["height"]
    pin.description = snapshot["description"]
    pin.sku = snapshot["sku"]

    currency = await session.get_one(entity=Currency, ident=snapshot["currency_id"])
    pin.currency = currency
    pin.currency_id = currency.id

    pin.front_image_guid = UUID(snapshot["front_image_guid"])
    pin.back_image_guid = (
        UUID(snapshot["back_image_guid"]) if snapshot["back_image_guid"] else None
    )

    pin.shops = set(
        (
            await session.scalars(
                select(Shop)
                .where(Shop.id.in_(snapshot["shop_ids"]))
                .execution_options(include_pending=True)
            )
        ).all()
    )
    await apply_pin_tags(pin.id, snapshot["tag_ids"], session)
    pin.artists = set(
        (
            await session.scalars(
                select(Artist)
                .where(Artist.id.in_(snapshot["artist_ids"]))
                .execution_options(include_pending=True)
            )
        ).all()
    )
    if snapshot.get("pin_set_ids"):
        pin.sets = set(
            (
                await session.scalars(
                    select(PinSet)
                    .where(PinSet.id.in_(snapshot["pin_set_ids"]))
                    .execution_options(include_pending=True)
                )
            ).all()
        )
    else:
        pin.sets = set()

    variant_ids = snapshot.get("variant_pin_ids") or []
    copy_ids = snapshot.get("unauthorized_copy_pin_ids") or []
    approved_variants: set[Pin] = (
        set(
            (
                await session.scalars(
                    select(Pin)
                    .where(Pin.id.in_(variant_ids))
                    .execution_options(include_pending=True)
                )
            ).all()
        )
        if variant_ids
        else set()
    )
    approved_copies: set[Pin] = (
        set(
            (
                await session.scalars(
                    select(Pin)
                    .where(Pin.id.in_(copy_ids))
                    .execution_options(include_pending=True)
                )
            ).all()
        )
        if copy_ids
        else set()
    )
    sync_symmetric_pin_links(
        pin=pin,
        variants=approved_variants,
        unauthorized_copies=approved_copies,
    )

    await _replace_links(pin, snapshot["links"], session)
    await upsert_grades(pin=pin, grades=snapshot["grades"], session=session)


async def _approve_artist_snapshot(
    artist: Artist, snapshot: dict[str, Any], session: AsyncSession
) -> None:
    artist.name = snapshot["name"]
    artist.description = snapshot["description"]
    artist.active = snapshot["active"]
    await _replace_links(artist, snapshot["links"], session)


async def _approve_shop_snapshot(
    shop: Shop, snapshot: dict[str, Any], session: AsyncSession
) -> None:
    shop.name = snapshot["name"]
    shop.description = snapshot["description"]
    shop.active = snapshot["active"]
    await _replace_links(shop, snapshot["links"], session)


async def _approve_tag_snapshot(
    tag: Tag, snapshot: dict[str, Any], session: AsyncSession
) -> None:
    tag.name = snapshot["name"]
    tag.description = snapshot["description"]
    tag.category = TagCategory(snapshot["category"])

    old_implication_ids: set[int] = {implied_tag.id for implied_tag in tag.implications}
    implied_tags = set(
        (
            await session.scalars(
                select(Tag)
                .where(Tag.id.in_(snapshot["implication_ids"]))
                .execution_options(include_pending=True)
            )
        ).all()
    )
    tag.implications = implied_tags
    await replace_tag_aliases(tag=tag, aliases=snapshot["aliases"], session=session)

    new_implication_ids: set[int] = {implied_tag.id for implied_tag in implied_tags}
    newly_added_ids: set[int] = new_implication_ids - old_implication_ids
    removed_ids: set[int] = old_implication_ids - new_implication_ids

    await session.flush()  # persist tag_implications changes before cascading

    await cascade_new_implications_to_pins(
        tag=tag,
        newly_added_ids=newly_added_ids,
        implied_tags=implied_tags,
        session=session,
    )

    if removed_ids:
        await _cascade_remove_implied(tag.id, removed_ids, session)
