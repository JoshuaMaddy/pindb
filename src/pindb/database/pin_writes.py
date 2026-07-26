"""Shared write helpers for Pin grade and relationship mutations.

Used by both the direct-edit path (routes/edit/pin.py) and the approval
path (database/pending_edit_utils.py) so the logic stays in one place.
"""

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from pindb.database.grade import Grade
from pindb.database.joins import pin_variants
from pindb.database.pin import Pin
from pindb.database.user_owned_pin import UserOwnedPin


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

    Must run inside the caller's write session while ``pin`` is attached.
    """
    _sync_one_side(pin=pin, attr="unauthorized_copies", target=unauthorized_copies)
    added_variants = _sync_one_side(pin=pin, attr="variants", target=variants)
    if added_variants:
        await session.flush()
        await _propagate_variant_clique(session=session, seed_pin_id=pin.id)


def _sync_one_side(*, pin: Pin, attr: str, target: set[Pin]) -> set[Pin]:
    current: set[Pin] = set(getattr(pin, attr))
    clean_target = {p for p in target if p.id != pin.id}
    added = clean_target - current
    removed = current - clean_target
    setattr(pin, attr, clean_target)
    for other in added:
        getattr(other, attr).add(pin)
    for other in removed:
        getattr(other, attr).discard(pin)
    return added


async def _propagate_variant_clique(*, session: AsyncSession, seed_pin_id: int) -> None:
    """Fully connect every pin transitively reachable from ``seed_pin_id``
    through the ``pin_variants`` graph.

    ``pin_variants`` stores each pair symmetrically (both directions), so a
    single-direction recursive walk from ``seed_pin_id`` over
    ``variant_pin_id`` visits the whole undirected connected component.
    Missing pairs within that component are then inserted (both directions,
    ``ON CONFLICT DO NOTHING``) turning the group into a full clique.
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
    component: set[int] = reachable | {seed_pin_id}
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
