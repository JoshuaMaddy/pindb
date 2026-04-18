"""Shared write helpers for Pin grade and relationship mutations.

Used by both the direct-edit path (routes/edit/pin.py) and the approval
path (database/pending_edit_utils.py) so the logic stays in one place.
"""

from sqlalchemy import update
from sqlalchemy.orm import Session

from pindb.database.grade import Grade
from pindb.database.pin import Pin
from pindb.database.user_owned_pin import UserOwnedPin


def upsert_grades(
    *,
    pin: Pin,
    grades: list[dict[str, object]],
    session: Session,
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
        session.execute(
            update(UserOwnedPin)
            .where(UserOwnedPin.grade_id == removed_grade.id)
            .values(grade_id=None)
        )
        session.delete(removed_grade)

    pin.grades = next_grades
