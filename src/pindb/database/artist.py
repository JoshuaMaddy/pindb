from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from pindb.database.base import Base
from pindb.database.joins import artists_links, pins_artists
from pindb.database.link import Link

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
    description: Mapped[str | None] = mapped_column(default=None)

    # Required Relationships
    pins: Mapped[set[Pin]] = relationship(
        secondary=pins_artists,
        default_factory=set,
        back_populates="artists",
    )

    # Optional Relationships
    links: Mapped[set[Link]] = relationship(
        secondary=artists_links,
        default_factory=set,
    )
