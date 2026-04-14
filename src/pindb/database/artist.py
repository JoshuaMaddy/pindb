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
from pindb.database.joins import artists_links, pins_artists
from pindb.database.link import Link

if TYPE_CHECKING:
    from pindb.database.pin import Pin


class Artist(PendingMixin, AuditMixin, MappedAsDataclass, Base):
    __tablename__ = "artists"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        init=False,
    )

    # Required Attributes
    name: Mapped[str]

    # Optional Attributes
    description: Mapped[str | None] = mapped_column(default=None)
    active: Mapped[bool] = mapped_column(default=True)

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

    def __hash__(self) -> int:
        return hash(self.name + str(self.id))

    def document(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "active": self.active,
            "is_pending": self.is_pending,
        }

    def __rich_repr__(self) -> Result:
        try:
            yield "id", self.id
            yield "name", self.name
            yield "is_pending", self.is_pending, False
            yield "active", self.active
        except Exception:
            yield "detached", True
            return
        if object_session(self):
            yield "number_of_pins", len(self.pins)
            yield "links", self.links, set()
