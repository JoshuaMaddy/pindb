from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from pindb.database.base import Base
from pindb.database.joins import pins_shops

if TYPE_CHECKING:
    from pindb.database.pin import Pin


class Shop(MappedAsDataclass, Base):
    __tablename__ = "shops"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        init=False,
    )

    # Required Attributes
    name: Mapped[str]

    # Required Relationships
    pins: Mapped[set[Pin]] = relationship(
        secondary=pins_shops,
        default_factory=set,
        back_populates="shops",
    )

    def __hash__(self) -> int:
        return hash(self.name) + (self.id or 0)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Shop):
            return False

        return value.id == self.id
