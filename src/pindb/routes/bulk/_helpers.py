"""Shared helpers for the bulk edit flow.

Resolves the pin ids for a given source (pin set / artist / shop / tag /
search), computes add/remove/replace tag changes, and applies a partial
set of scalar field updates without touching fields the user left alone.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pindb.database.artist import Artist
from pindb.database.joins import (
    pin_set_memberships,
    pins_artists,
    pins_shops,
    pins_tags,
)
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.database.tag import Tag
from pindb.model_utils import parse_magnitude_mm
from pindb.models.acquisition_type import AcquisitionType
from pindb.models.funding_type import FundingType


class BulkEditSource(StrEnum):
    pin_set = "pin_set"
    artist = "artist"
    shop = "shop"
    tag = "tag"


class TagMode(StrEnum):
    add = "add"
    remove = "remove"
    replace = "replace"


# Fields exposed through the bulk edit form. Anything not on this list is
# out of scope; see the plan doc for rationale.
BULK_SCALAR_FIELDS: tuple[str, ...] = (
    "acquisition_type",
    "limited_edition",
    "number_produced",
    "release_date",
    "end_date",
    "funding_type",
    "posts",
    "width",
    "height",
)


async def resolve_pin_ids(
    session: AsyncSession,
    source: BulkEditSource,
    source_id: int,
) -> list[int]:
    """Return the pin ids for the given entity source, in a stable order."""
    if source == BulkEditSource.pin_set:
        return list(
            (
                await session.scalars(
                    select(pin_set_memberships.c.pin_id)
                    .where(pin_set_memberships.c.set_id == source_id)
                    .order_by(pin_set_memberships.c.position.asc())
                )
            ).all()
        )
    if source == BulkEditSource.artist:
        return list(
            (
                await session.scalars(
                    select(pins_artists.c.pin_id).where(
                        pins_artists.c.artists_id == source_id
                    )
                )
            ).all()
        )
    if source == BulkEditSource.shop:
        return list(
            (
                await session.scalars(
                    select(pins_shops.c.pin_id).where(pins_shops.c.shop_id == source_id)
                )
            ).all()
        )
    if source == BulkEditSource.tag:
        return list(
            (
                await session.scalars(
                    select(pins_tags.c.pin_id)
                    .where(pins_tags.c.tag_id == source_id)
                    .distinct()
                )
            ).all()
        )
    raise ValueError(f"Unknown bulk edit source: {source}")


async def resolve_source_name(
    session: AsyncSession,
    source: BulkEditSource,
    source_id: int,
) -> str:
    """Human-readable name for a source entity, for the form header."""
    model: type[PinSet | Artist | Shop | Tag]
    if source == BulkEditSource.pin_set:
        model = PinSet
    elif source == BulkEditSource.artist:
        model = Artist
    elif source == BulkEditSource.shop:
        model = Shop
    elif source == BulkEditSource.tag:
        model = Tag
    else:
        raise ValueError(f"Unknown bulk edit source: {source}")
    entity = await session.get(model, source_id)  # type: ignore[arg-type]
    if entity is None:
        return f"#{source_id}"
    if isinstance(entity, Tag):
        return entity.display_name
    return entity.name


def source_redirect_route(source: BulkEditSource) -> str:
    # Use the bare-id route variants so callers can pass `id=` only; the
    # canonical slug redirect on the GET will rewrite to the slugged form.
    return {
        BulkEditSource.pin_set: "get_pin_set_by_id",
        BulkEditSource.artist: "get_artist_by_id",
        BulkEditSource.shop: "get_shop_by_id",
        BulkEditSource.tag: "get_tag_by_id",
    }[source]


def compute_tag_change(
    current: set[int],
    submitted: set[int],
    mode: TagMode,
) -> set[int]:
    """Return the new explicit-tag id set for a pin under the chosen mode."""
    if mode == TagMode.add:
        return current | submitted
    if mode == TagMode.remove:
        return current - submitted
    if mode == TagMode.replace:
        return set(submitted)
    raise ValueError(f"Unknown tag mode: {mode}")


def _coerce_bulk_scalar(field: str, raw: object) -> object:
    """Coerce a form-provided value to the type Pin expects."""
    if raw is None or raw == "":
        return None
    if field == "acquisition_type":
        return raw if isinstance(raw, AcquisitionType) else AcquisitionType(str(raw))
    if field == "funding_type":
        return raw if isinstance(raw, FundingType) else FundingType(str(raw))
    if field == "limited_edition":
        if isinstance(raw, bool):
            return raw
        return str(raw).lower() in {"1", "true", "yes", "on"}
    if field in {"number_produced", "posts"}:
        return int(str(raw))
    if field in {"width", "height"}:
        # apply_bulk_scalars re-invokes coerce on already-stored mm floats.
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            return float(raw)
        label = "Width" if field == "width" else "Height"
        return parse_magnitude_mm(
            field_label=label,
            raw=str(raw) if raw is not None else None,
        )
    if field in {"release_date", "end_date"}:
        if isinstance(raw, date):
            return raw
        return date.fromisoformat(str(raw))
    return raw


def apply_bulk_scalars(pin: Pin, field_updates: dict[str, Any]) -> None:
    """Assign only the fields that were explicitly submitted to pin."""
    for field in BULK_SCALAR_FIELDS:
        if field not in field_updates:
            continue
        setattr(pin, field, _coerce_bulk_scalar(field, field_updates[field]))


def snapshot_scalar_updates(field_updates: dict[str, Any]) -> dict[str, Any]:
    """JSON-safe version of scalar updates for inclusion in a PendingEdit patch."""
    out: dict[str, Any] = {}
    for field in BULK_SCALAR_FIELDS:
        if field not in field_updates:
            continue
        value = field_updates[field]
        if isinstance(value, AcquisitionType):
            out[field] = value.value
        elif isinstance(value, FundingType):
            out[field] = value.value
        elif isinstance(value, date):
            out[field] = value.isoformat()
        else:
            out[field] = value
    return out
