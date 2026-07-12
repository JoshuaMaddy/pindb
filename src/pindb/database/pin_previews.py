"""Pin counts and thumbnail samples for entity list cards.

List pages (tags, shops, artists, pin sets) show each entity as a card with a pin
count and a 2x2 grid of up to four thumbnails. The obvious way to feed those --
``selectinload(Tag.pins)`` -- hydrates every ``Pin`` the entity has ever been
attached to, so a tag with 500 pins costs 500 ORM objects to render one number and
four images, times the whole page. ``load_pin_previews`` gets the same two things
in two bounded queries instead.

The counts are deliberately *not* denormalized onto the entity tables. What a
viewer may see is role-dependent (``audit_events._filter_deleted`` hides
soft-deleted rows from everyone and unapproved rows from non-editors), so there is
no single correct number to store -- an editor and a guest looking at the same tag
should see different counts. Both queries here select ``Pin`` as a mapped entity,
which is what makes that filter apply to them automatically.
"""

from __future__ import annotations

from random import sample
from typing import Sequence

from sqlalchemy import Column, Table, select
from sqlalchemy.ext.asyncio import AsyncSession

from pindb.database.pin import Pin

PREVIEW_PINS: int = 4
"""Thumbnails in an entity card's 2x2 grid."""


class PinPreviews:
    """Per-entity pin counts and thumbnail samples for one page of list cards."""

    def __init__(
        self,
        counts: dict[int, int],
        previews: dict[int, list[Pin]],
    ) -> None:
        self._counts = counts
        self._previews = previews

    def count(self, entity_id: int) -> int:
        """Pins on this entity that are visible to the current viewer."""
        return self._counts.get(entity_id, 0)

    def pins(self, entity_id: int) -> list[Pin]:
        """Up to ``PREVIEW_PINS`` of them, sampled at random, fully loaded."""
        return self._previews.get(entity_id, [])


async def load_pin_previews(
    session: AsyncSession,
    *,
    join_table: Table,
    entity_column: Column[int],
    entity_ids: Sequence[int],
) -> PinPreviews:
    """Load pin counts and a random thumbnail sample for each of ``entity_ids``.

    ``entity_column`` is the join table's non-pin side (``pins_tags.c.tag_id``,
    ``pins_shops.c.shop_id``, ...); each is indexed for exactly this lookup.

    Query one returns ``(entity_id, pin_id)`` pairs and nothing else -- ids are
    cheap, and grouping them here gives the counts and the random sample without a
    second aggregate. Query two hydrates only the pins that will actually be drawn,
    so at most ``len(entity_ids) * PREVIEW_PINS`` ``Pin`` objects are built no
    matter how many pins the entities have between them.
    """
    if not entity_ids:
        return PinPreviews({}, {})

    pairs = (
        await session.execute(
            select(entity_column, Pin.id)
            .join(join_table, Pin.id == join_table.c.pin_id)
            .where(entity_column.in_(entity_ids))
        )
    ).all()

    pin_ids_by_entity: dict[int, list[int]] = {}
    for entity_id, pin_id in pairs:
        pin_ids_by_entity.setdefault(entity_id, []).append(pin_id)

    counts: dict[int, int] = {
        entity_id: len(pin_ids) for entity_id, pin_ids in pin_ids_by_entity.items()
    }

    sampled_by_entity: dict[int, list[int]] = {
        entity_id: (
            sample(pin_ids, k=PREVIEW_PINS)
            if len(pin_ids) > PREVIEW_PINS
            else list(pin_ids)
        )
        for entity_id, pin_ids in pin_ids_by_entity.items()
    }

    wanted: set[int] = {
        pin_id for pin_ids in sampled_by_entity.values() for pin_id in pin_ids
    }
    if not wanted:
        return PinPreviews(counts, {})

    rows = (await session.scalars(select(Pin).where(Pin.id.in_(wanted)))).all()
    pins_by_id: dict[int, Pin] = {pin.id: pin for pin in rows}

    previews: dict[int, list[Pin]] = {
        entity_id: [pins_by_id[pin_id] for pin_id in pin_ids if pin_id in pins_by_id]
        for entity_id, pin_ids in sampled_by_entity.items()
    }
    return PinPreviews(counts, previews)
