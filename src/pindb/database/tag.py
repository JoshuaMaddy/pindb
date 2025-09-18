from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from pindb.database.base import Base
from pindb.database.joins import pins_tags

if TYPE_CHECKING:
    from pindb.database.pin import Pin


class Tag(MappedAsDataclass, Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    # Required Attributes
    name: Mapped[str]

    # Foreign key for self-referential parent
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("tags.id"),
        nullable=True,
        default=None,
    )

    # Required Relationships
    pins: Mapped[set[Pin]] = relationship(
        secondary=pins_tags,
        default_factory=set,
        back_populates="tags",
    )

    # Self-referential Relationships
    parent: Mapped[Tag | None] = relationship(
        "Tag",
        remote_side=[id],
        back_populates="children",
        default=None,
    )
    children: Mapped[set[Tag]] = relationship(
        "Tag",
        back_populates="parent",
        cascade="all, delete-orphan",
        default_factory=set,
    )

    def __hash__(self) -> int:
        return hash(self.name) + (self.id or 0)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Tag):
            return False
        return value.id == self.id
