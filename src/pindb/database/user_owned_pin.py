from __future__ import annotations

from typing import TYPE_CHECKING

from rich.repr import Result
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)

from pindb.database.audit_mixin import AuditMixin
from pindb.database.base import Base

if TYPE_CHECKING:
    from pindb.database.grade import Grade
    from pindb.database.pin import Pin
    from pindb.database.user import User


class UserOwnedPin(AuditMixin, MappedAsDataclass, Base):
    __tablename__ = "user_owned_pins"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "pin_id",
            "grade_id",
            postgresql_nulls_not_distinct=True,
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        init=False,
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    pin_id: Mapped[int] = mapped_column(ForeignKey("pins.id"))
    grade_id: Mapped[int | None] = mapped_column(
        ForeignKey("grades.id"),
        default=None,
    )
    quantity: Mapped[int] = mapped_column(default=1)
    tradeable_quantity: Mapped[int] = mapped_column(default=0)

    user: Mapped[User] = relationship(
        back_populates="owned_pins",
        init=False,
        foreign_keys=[user_id],
    )
    pin: Mapped[Pin] = relationship(init=False)
    grade: Mapped[Grade | None] = relationship(init=False)

    def __hash__(self) -> int:
        return self.id or 0

    def __rich_repr__(self) -> Result:
        try:
            yield "id", self.id
            yield "user_id", self.user_id
            yield "pin_id", self.pin_id
            yield "grade_id", self.grade_id
            yield "quantity", self.quantity
            yield "tradeable_quantity", self.tradeable_quantity
        except Exception:
            yield "detached", True
