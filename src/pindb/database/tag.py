from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Iterable

from rich.repr import Result
from sqlalchemy import Enum as SQLAlchemyEnum, ForeignKey, Index, select
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    Session,
    mapped_column,
    object_session,
    relationship,
)

from pindb.database.audit_mixin import AuditMixin
from pindb.database.base import Base
from pindb.database.joins import pins_tags, tag_implications
from pindb.database.pending_mixin import PendingMixin

if TYPE_CHECKING:
    from pindb.database.pin import Pin


class TagCategory(str, Enum):
    general = "general"
    copyright = "copyright"
    character = "character"
    species = "species"
    meta = "meta"
    material = "material"


class TagAlias(MappedAsDataclass, Base):
    __tablename__ = "tag_aliases"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), init=False)
    alias: Mapped[str] = mapped_column(unique=True)

    def __rich_repr__(self) -> Result:
        yield "id", self.id
        yield "tag_id", self.tag_id
        yield "alias", self.alias


class Tag(PendingMixin, AuditMixin, MappedAsDataclass, Base):
    __tablename__ = "tags"
    __table_args__ = (
        Index(
            "uq_tags_name_active",
            "name",
            unique=True,
            postgresql_where="deleted_at IS NULL",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    name: Mapped[str] = mapped_column()
    description: Mapped[str | None] = mapped_column(default=None)
    category: Mapped[TagCategory] = mapped_column(
        SQLAlchemyEnum(TagCategory, name="tagcategory", native_enum=False),
        default=TagCategory.general,
    )

    aliases: Mapped[list[TagAlias]] = relationship(
        default_factory=list,
        cascade="all, delete-orphan",
    )

    pins: Mapped[set[Pin]] = relationship(
        secondary=pins_tags,
        default_factory=set,
        back_populates="tags",
    )

    implications: Mapped[set[Tag]] = relationship(
        "Tag",
        secondary=tag_implications,
        primaryjoin=lambda: Tag.id == tag_implications.c.tag_id,
        secondaryjoin=lambda: Tag.id == tag_implications.c.implied_tag_id,
        back_populates="implied_by",
        default_factory=set,
    )
    implied_by: Mapped[set[Tag]] = relationship(
        "Tag",
        secondary=tag_implications,
        primaryjoin=lambda: Tag.id == tag_implications.c.implied_tag_id,
        secondaryjoin=lambda: Tag.id == tag_implications.c.tag_id,
        back_populates="implications",
        default_factory=set,
    )

    def __hash__(self) -> int:
        return hash(self.name) + (self.id or 0)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Tag):
            return False
        return value.id == self.id

    def document(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "is_pending": self.is_pending,
            "aliases": [a.alias for a in self.aliases],
        }

    def __rich_repr__(self) -> Result:
        try:
            yield "id", self.id
            yield "name", self.name
            yield "description", self.description, None
            yield "category", self.category, TagCategory.general
            yield "is_pending", self.is_pending, False
        except Exception:
            yield "detached", True
            return
        if object_session(self):
            yield "number_of_pins", len(self.pins)
            yield "aliases", self.aliases, []
            yield "implications", self.implications, set()
            yield "implied_by", self.implied_by, set()


def resolve_implications(initial: Iterable[Tag], session: Session) -> set[Tag]:
    """BFS transitive closure of tag implications. Cycle-safe."""
    resolved: set[Tag] = set(initial)
    queue: list[Tag] = list(initial)
    seen_ids: set[int] = set()
    while queue:
        tag = queue.pop()
        if tag.id in seen_ids:
            continue
        seen_ids.add(tag.id)
        implied = session.scalars(
            select(Tag)
            .join(tag_implications, Tag.id == tag_implications.c.implied_tag_id)
            .where(tag_implications.c.tag_id == tag.id)
        ).all()
        for t in implied:
            if t.id not in seen_ids:
                resolved.add(t)
                queue.append(t)
    return resolved
