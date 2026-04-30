"""Shared write helpers for Pin grade and relationship mutations.

Used by both the direct-edit path (routes/edit/pin.py) and the approval
path (database/pending_edit_utils.py) so the logic stays in one place.
"""

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from pindb.database.grade import Grade
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


def sync_symmetric_pin_links(
    *,
    pin: Pin,
    variants: set[Pin],
    unauthorized_copies: set[Pin],
) -> None:
    """Replace ``pin``'s variant / copy sets and mirror the counterpart side.

    Each symmetric pair is stored as two rows (A→B and B→A) so ordinary
    relationships work without ``or_`` primaryjoins. This helper keeps both
    directions in lock-step: adds mirror rows for newcomers, drops mirror
    rows for removals. Self-refs are filtered defensively.

    Must run inside the caller's write session while ``pin`` is attached.
    """
    _sync_one_side(pin=pin, attr="variants", target=variants)
    _sync_one_side(pin=pin, attr="unauthorized_copies", target=unauthorized_copies)


def _sync_one_side(*, pin: Pin, attr: str, target: set[Pin]) -> None:
    current: set[Pin] = set(getattr(pin, attr))
    clean_target = {p for p in target if p.id != pin.id}
    added = clean_target - current
    removed = current - clean_target
    setattr(pin, attr, clean_target)
    for other in added:
        getattr(other, attr).add(pin)
    for other in removed:
        getattr(other, attr).discard(pin)
