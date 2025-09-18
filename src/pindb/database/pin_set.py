from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from pindb.database.base import Base
from pindb.database.joins import pin_sets_links, pins_sets
from pindb.database.link import Link

if TYPE_CHECKING:
    from pindb.database.pin import Pin


class PinSet(MappedAsDataclass, Base):
    __tablename__ = "pin_sets"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        init=False,
    )

    # Required Attributes
    name: Mapped[str]

    # Optional Attributes
    description: Mapped[str | None] = mapped_column(default=None)

    # Required Relationships
    pins: Mapped[set[Pin]] = relationship(
        secondary=pins_sets,
        default_factory=set,
        back_populates="sets",
    )

    # Optional Relationships
    links: Mapped[set[Link]] = relationship(
        secondary=pin_sets_links,
        default_factory=set,
    )

    def __hash__(self) -> int:
        return hash(self.name) + (self.id or 0)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Pin):
            return False

        return value.id == self.id
