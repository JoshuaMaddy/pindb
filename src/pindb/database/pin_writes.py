"""Shared write helpers for Pin grade and relationship mutations.

Used by both the direct-edit path (routes/edit/pin.py) and the approval
path (database/pending_edit_utils.py) so the logic stays in one place.
"""

from dataclasses import dataclass

from sqlalchemy import Table, and_, delete, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from pindb.database.grade import Grade
from pindb.database.joins import pin_unauthorized_copies, pin_variants
from pindb.database.pin import Pin
from pindb.database.user_owned_pin import UserOwnedPin

# Relationship attribute -> (join table, the column holding the *other* pin).
_SYMMETRIC_LINKS: dict[str, tuple[Table, str]] = {
    "variants": (pin_variants, "variant_pin_id"),
    "unauthorized_copies": (pin_unauthorized_copies, "copy_pin_id"),
}


async def upsert_grades(
    *,
    pin: Pin,
    grades: list[dict[str, object]],
    session: AsyncSession,
) -> None:
    """Match incoming grade dicts by name: update prices on existing grades,
    add new ones, and soft-remove old ones (nullifying grade_id on
    UserOwnedPin rows first).

    Each dict in *grades* must have ``{"name": str, "price": float | None}``.
    """
    existing_by_name: dict[str, Grade] = {grade.name: grade for grade in pin.grades}
    next_grades: set[Grade] = set()

    for grade_dict in grades:
        name: str = str(grade_dict["name"])
        raw_price = grade_dict.get("price")
        price: float | None = float(str(raw_price)) if raw_price is not None else None
        if name in existing_by_name:
            existing_grade = existing_by_name[name]
            existing_grade.price = price
            next_grades.add(existing_grade)
        else:
            next_grades.add(Grade(name=name, price=price))

    for removed_grade in pin.grades - next_grades:
        await session.execute(
            update(UserOwnedPin)
            .where(UserOwnedPin.grade_id == removed_grade.id)
            .values(grade_id=None)
        )
        await session.delete(removed_grade)

    pin.grades = next_grades


@dataclass(frozen=True, slots=True)
class _LinkDelta:
    added: set[int]
    removed: set[int]


async def sync_symmetric_pin_links(
    *,
    session: AsyncSession,
    pin: Pin,
    variants: set[Pin],
    unauthorized_copies: set[Pin],
) -> None:
    """Replace ``pin``'s variant / copy sets and mirror the counterpart side.

    Each symmetric pair is stored as two rows (A→B and B→A) so ordinary
    relationships work without ``or_`` primaryjoins. This helper keeps both
    directions in lock-step: adds mirror rows for newcomers, drops mirror
    rows for removals. Self-refs are filtered defensively.

    Variant links are additionally transitive: linking pin A to a pin B
    that already has variants merges the whole group into one clique (every
    member linked to every other member), rather than leaving A linked only
    to B. Unauthorized-copy links stay pairwise — a copy relationship
    between two specific pins doesn't imply anything about a third pin.

    Variant *removal* is transitive for the same reason: dropping B from A's
    form drops B from A's whole variant group. Deleting only the A↔B pair
    would leave B connected to A through any third member (A–C, B–C), so B
    would still be in A's connected component and the next edit anywhere in
    that group would propagate the A↔B edge straight back.

    Only ``pin``'s own collection is mutated through the ORM; the mirror
    rows are written with Core statements against the join table. Touching
    ``other.variants`` instead would lazy-load that counterpart collection,
    which raises ``MissingGreenlet`` under asyncio for every pin that wasn't
    eagerly loaded — and the pins being *removed* never are, because they
    come off ``pin``'s own collection rather than the caller's id lookup.
    Going through Core also sidesteps ``Pin.__hash__`` being derived from
    ``Pin.name``: the edit routes assign the new name before calling this,
    so a renamed pin sitting in an already-loaded counterpart set hashes to
    a bucket it isn't in.

    Must run inside the caller's write session while ``pin`` is attached.
    """
    copy_delta = _sync_one_side(
        pin=pin, attr="unauthorized_copies", target=unauthorized_copies
    )
    variant_delta = _sync_one_side(pin=pin, attr="variants", target=variants)

    # Flush pin's own side first so the clique walk below sees its new edges.
    await session.flush()

    await _mirror_other_side(
        session=session, attr="unauthorized_copies", pin_id=pin.id, delta=copy_delta
    )
    await _mirror_other_side(
        session=session, attr="variants", pin_id=pin.id, delta=variant_delta
    )

    if variant_delta.removed:
        await _detach_from_variant_group(
            session=session, seed_pin_id=pin.id, removed_pin_ids=variant_delta.removed
        )
    if variant_delta.added:
        await _propagate_variant_clique(session=session, seed_pin_id=pin.id)


def _sync_one_side(*, pin: Pin, attr: str, target: set[Pin]) -> _LinkDelta:
    """Replace ``pin.<attr>`` with *target* and report the id-level delta."""
    current_ids: set[int] = {other.id for other in getattr(pin, attr)}
    clean_target: set[Pin] = {other for other in target if other.id != pin.id}
    target_ids: set[int] = {other.id for other in clean_target}
    setattr(pin, attr, clean_target)
    return _LinkDelta(added=target_ids - current_ids, removed=current_ids - target_ids)


async def _mirror_other_side(
    *, session: AsyncSession, attr: str, pin_id: int, delta: _LinkDelta
) -> None:
    """Write the counterpart rows (other → pin) for one relationship."""
    table, other_column = _SYMMETRIC_LINKS[attr]
    if delta.removed:
        await session.execute(
            delete(table).where(
                table.c.pin_id.in_(delta.removed),
                table.c[other_column] == pin_id,
            )
        )
    if delta.added:
        stmt = pg_insert(table).values(
            [
                {"pin_id": other_id, other_column: pin_id}
                for other_id in sorted(delta.added)
            ]
        )
        await session.execute(
            stmt.on_conflict_do_nothing(
                index_elements=[table.c.pin_id, table.c[other_column]]
            )
        )


async def _variant_component(*, session: AsyncSession, seed_pin_id: int) -> set[int]:
    """Every pin transitively reachable from ``seed_pin_id`` through
    ``pin_variants``, including the seed itself.

    ``pin_variants`` stores each pair symmetrically (both directions), so a
    single-direction recursive walk from ``seed_pin_id`` over
    ``variant_pin_id`` visits the whole undirected connected component.
    """
    base = select(pin_variants.c.variant_pin_id.label("pin_id")).where(
        pin_variants.c.pin_id == seed_pin_id
    )
    component_cte = base.cte(name="variant_component", recursive=True)
    component_cte = component_cte.union(
        select(pin_variants.c.variant_pin_id).join(
            component_cte, pin_variants.c.pin_id == component_cte.c.pin_id
        )
    )
    reachable: set[int] = set(
        (await session.scalars(select(component_cte.c.pin_id))).all()
    )
    return reachable | {seed_pin_id}


async def _detach_from_variant_group(
    *, session: AsyncSession, seed_pin_id: int, removed_pin_ids: set[int]
) -> None:
    """Cut every edge between ``removed_pin_ids`` and the variant group that
    ``seed_pin_id`` belongs to, leaving the rest of the group intact.

    Runs *after* the seed's own side has flushed, so the walk sees a group
    the removed pins can still reach only through their surviving siblings —
    which is exactly the connection that has to go. Edges between two pins
    removed in the same edit are cut too: both of them left the group.
    """
    component: set[int] = await _variant_component(
        session=session, seed_pin_id=seed_pin_id
    )
    doomed: set[int] = removed_pin_ids & component
    if not doomed:
        return

    await session.execute(
        delete(pin_variants).where(
            or_(
                and_(
                    pin_variants.c.pin_id.in_(doomed),
                    pin_variants.c.variant_pin_id.in_(component),
                ),
                and_(
                    pin_variants.c.pin_id.in_(component),
                    pin_variants.c.variant_pin_id.in_(doomed),
                ),
            )
        )
    )


async def _propagate_variant_clique(*, session: AsyncSession, seed_pin_id: int) -> None:
    """Fully connect every pin transitively reachable from ``seed_pin_id``
    through the ``pin_variants`` graph.

    Missing pairs within the connected component are inserted (both
    directions, ``ON CONFLICT DO NOTHING``) turning the group into a full
    clique.
    """
    component: set[int] = await _variant_component(
        session=session, seed_pin_id=seed_pin_id
    )
    if len(component) < 2:
        return

    edge_rows = [
        {"pin_id": a, "variant_pin_id": b}
        for a in component
        for b in component
        if a != b
    ]
    stmt = pg_insert(pin_variants).values(edge_rows)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=[pin_variants.c.pin_id, pin_variants.c.variant_pin_id]
    )
    await session.execute(stmt)
