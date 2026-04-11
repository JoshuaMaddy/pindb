from __future__ import annotations

from typing import TYPE_CHECKING

from rich.repr import Result
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
    object_session,
    relationship,
)

from pindb.database.audit_mixin import AuditMixin
from pindb.database.base import Base
from pindb.database.pending_mixin import PendingMixin
from pindb.database.joins import pins_materials

if TYPE_CHECKING:
    from pindb.database.pin import Pin


class Material(PendingMixin, AuditMixin, MappedAsDataclass, Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    name: Mapped[str] = mapped_column(unique=True)

    pins: Mapped[set[Pin]] = relationship(
        secondary=pins_materials,
        init=False,
        back_populates="materials",
    )

    def __hash__(self) -> int:
        return hash(self.name) + (self.id or 0)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Material):
            return False

        return value.id == self.id

    def __rich_repr__(self) -> Result:
        try:
            yield "id", self.id
            yield "name", self.name
            yield "is_pending", self.is_pending, False
        except Exception:
            yield "detached", True
            return
        if object_session(self):
            yield "number_of_pins", len(self.pins)
