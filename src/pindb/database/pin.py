from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from pindb.database.artist import Artist
from pindb.database.base import Base
from pindb.database.joins import pins_artists, pins_materials, pins_sets, pins_shops
from pindb.models import AcquisitionType, FundingType

if TYPE_CHECKING:
    from pindb.database.material import Material
    from pindb.database.pin_set import PinSet
    from pindb.database.shop import Shop


class Pin(MappedAsDataclass, Base):
    __tablename__ = "pins"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    # Required Attributes
    name: Mapped[str]
    acquisition_type: Mapped[AcquisitionType]

    # Required Relationships
    materials: Mapped[set[Material]] = relationship(
        secondary=pins_materials,
        back_populates="pins",
    )
    shops: Mapped[set[Shop]] = relationship(
        secondary=pins_shops,
        back_populates="pins",
    )

    # Optional Attributes
    ## Production
    limited_edition: Mapped[bool] = mapped_column(default=False)
    number_produced: Mapped[int | None] = mapped_column(default=None)
    release_date: Mapped[datetime | None] = mapped_column(default=None)
    end_date: Mapped[datetime | None] = mapped_column(default=None)
    funding_type: Mapped[FundingType] = mapped_column(default=FundingType.self)
    ## Physical
    posts: Mapped[int] = mapped_column(default=1)
    width: Mapped[float | None] = mapped_column(default=None)
    height: Mapped[float | None] = mapped_column(default=None)
    depth: Mapped[float | None] = mapped_column(default=None)

    # Optional Relationships
    artists: Mapped[set[Artist]] = relationship(
        secondary=pins_artists,
        back_populates="pins",
        default_factory=set,
    )
    sets: Mapped[set[PinSet]] = relationship(
        secondary=pins_sets,
        back_populates="pins",
        default_factory=set,
    )

    def __hash__(self) -> int:
        return hash(self.name) + (self.id or 0)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Pin):
            return False

        return value.id == self.id
