from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
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
from pindb.database.joins import pin_set_memberships, pin_sets_links
from pindb.database.link import Link

if TYPE_CHECKING:
    from pindb.database.pin import Pin
    from pindb.database.user import User


class PinSet(PendingMixin, AuditMixin, MappedAsDataclass, Base):
    __tablename__ = "pin_sets"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        init=False,
    )

    # Required Attributes
    name: Mapped[str]

    # Optional Attributes
    description: Mapped[str | None] = mapped_column(default=None)

    # Owner — None means curator/admin set, set means personal user set
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)

    # Required Relationships
    pins: Mapped[list[Pin]] = relationship(
        secondary=pin_set_memberships,
        default_factory=list,
        back_populates="sets",
    )

    # Optional Relationships
    links: Mapped[set[Link]] = relationship(
        secondary=pin_sets_links,
        default_factory=set,
    )
    owner: Mapped[User | None] = relationship(
        back_populates="personal_sets",
        foreign_keys=[owner_id],
        init=False,
    )

    def __hash__(self) -> int:
        return hash(self.name) + (self.id or 0)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, PinSet):
            return False

        return value.id == self.id

    def __rich_repr__(self) -> Result:
        try:
            yield "id", self.id
            yield "name", self.name
            yield "is_pending", self.is_pending, False
            yield "owner_id", self.owner_id, None
        except Exception:
            yield "detached", True
            return
        if object_session(self):
            yield "number_of_pins", len(self.pins)
            yield "owner", self.owner.username if self.owner else None, None
            yield "links", self.links, set()
