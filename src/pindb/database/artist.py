from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from pindb.database.base import Base
from pindb.database.joins import pins_artists

if TYPE_CHECKING:
    from pindb.database.pin import Pin


class Artist(MappedAsDataclass, Base):
    __tablename__ = "artists"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        init=False,
    )

    # Required Attributes
    name: Mapped[str]

    # Optional Attributes

    # Required Relationships
    pins: Mapped[set[Pin]] = relationship(
        secondary=pins_artists,
        default_factory=set,
        back_populates="artists",
    )
