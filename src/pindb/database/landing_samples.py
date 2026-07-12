"""Random entity samples for the ``/list`` landing hub.

The hub shows one column per browsable entity type (shop / tag / pin set /
artist) with a handful of examples underneath. Picking those examples pulls
double duty with ``pin_previews.load_pin_previews`` -- that module answers "how
many pins does this specific entity have and what do four of them look like",
this one answers "which entities are even worth showing" (skip anything with a
sparse pin count, since the whole point is to show the 2x2 thumbnail grid
full). ``model`` is joined into the query (not just ``join_table``) so
``audit_events._filter_deleted`` sees a mapped entity to attach its
soft-delete/pending ``with_loader_criteria`` to, same as every other pin-count
query in the app.
"""

from __future__ import annotations

from typing import Sequence, TypeVar

from sqlalchemy import Column, ColumnElement, Table, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from pindb.database.artist import Artist
from pindb.database.pin import Pin
from pindb.database.pin_previews import PREVIEW_PINS
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.database.tag import Tag

_SampleEntity = TypeVar("_SampleEntity", Shop, Tag, Artist, PinSet)

NARROW_SAMPLES: int = 4
"""Samples shown while a hub column is one card wide."""

SAMPLE_SIZE: int = 8
"""Samples loaded per column: four rows of two once the column goes two wide (2xl)."""


async def sample_random_pins(session: AsyncSession, *, limit: int) -> list[Pin]:
    """Random pins that have a front image, ready to draw as preview cards.

    ``shops``/``artists`` are eager-loaded because ``pin_preview_card`` reads both;
    without that every card is two more queries (and a ``DetachedInstanceError`` if
    the template renders after the session closes).
    """
    rows = await session.scalars(
        select(Pin)
        .where(Pin.front_image_guid.is_not(None))
        .order_by(func.random())
        .limit(limit)
        .options(selectinload(Pin.shops), selectinload(Pin.artists))
    )
    return list(rows.all())


async def sample_entities_with_pins(
    session: AsyncSession,
    *,
    model: type[_SampleEntity],
    join_table: Table,
    entity_column: Column[int],
    sample_size: int = SAMPLE_SIZE,
    min_pins: int = PREVIEW_PINS,
    extra_where: ColumnElement[bool] | None = None,
) -> list[_SampleEntity]:
    """Random sample of *model* rows with more than *min_pins* visible pins."""
    id_query = (
        select(model.id)
        .select_from(model)
        .join(join_table, entity_column == model.id)
        .join(Pin, Pin.id == join_table.c.pin_id)
    )
    if extra_where is not None:
        id_query = id_query.where(extra_where)
    id_query = (
        id_query.group_by(model.id)
        .having(func.count(Pin.id) > min_pins)
        .order_by(func.random())
        .limit(sample_size)
    )

    ids: Sequence[int] = (await session.scalars(id_query)).all()
    if not ids:
        return []

    rows = (await session.scalars(select(model).where(model.id.in_(ids)))).all()
    order: dict[int, int] = {entity_id: index for index, entity_id in enumerate(ids)}
    return sorted(rows, key=lambda row: order[row.id])
