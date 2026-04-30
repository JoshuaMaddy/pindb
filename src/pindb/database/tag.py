"""Hierarchical tags, aliases, implications, and pin tagging helpers."""

from __future__ import annotations

from enum import Enum
from inspect import isawaitable
from typing import TYPE_CHECKING, Any, Iterable, cast

from rich.repr import Result
from sqlalchemy import (
    Computed,
    ForeignKey,
    Index,
    UniqueConstraint,
    delete,
    insert,
    literal,
    select,
)
from sqlalchemy import (
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import ScalarResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    Session,
    mapped_column,
    object_session,
    relationship,
)
from titlecase import titlecase

from pindb.database._aliases import replace_aliases
from pindb.database.audit_mixin import AuditMixin
from pindb.database.base import Base
from pindb.database.joins import pins_tags, tag_implications
from pindb.database.pending_mixin import PendingMixin

if TYPE_CHECKING:
    from pindb.database.pin import Pin


async def _tag_scalars(
    *, session: AsyncSession | Session, statement: Any
) -> list["Tag"]:
    scalars_result = session.scalars(statement)
    if isawaitable(scalars_result):
        scalars_result = await scalars_result
    typed_result = cast(ScalarResult["Tag"], scalars_result)
    return list(typed_result.all())


class TagCategory(str, Enum):
    """Fixed tag kinds (material, color, character, …) including ``material`` for finishes."""

    general = "general"
    copyright = "copyright"
    character = "character"
    archetype = "archetype"
    species = "species"
    company = "company"
    meta = "meta"
    material = "material"
    color = "color"


class TagAlias(MappedAsDataclass, Base):
    """Alternate searchable string for a tag (unique per tag)."""

    __tablename__ = "tag_aliases"
    __table_args__ = (
        UniqueConstraint("tag_id", "alias", name="uq_tag_aliases_tag_id_alias"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), init=False)
    alias: Mapped[str] = mapped_column()

    def __rich_repr__(self) -> Result:
        yield "id", self.id
        yield "tag_id", self.tag_id
        yield "alias", self.alias


def normalize_tag_name(name: str) -> str:
    """Normalize to e621 form: lowercase, spaces → underscores."""
    return name.strip().lower().replace(" ", "_")


async def replace_tag_aliases(
    tag: Tag, aliases: Iterable[str], session: AsyncSession
) -> None:
    """Replace persisted aliases for ``tag`` (normalized to e621 form)."""
    await replace_aliases(
        owner=tag,
        alias_cls=TagAlias,
        raw_aliases=aliases,
        session=session,
        normalizer=normalize_tag_name,
    )


class Tag(PendingMixin, AuditMixin, MappedAsDataclass, Base):
    """Faceted classification node with optional implications between tags."""

    __tablename__ = "tags"
    __table_args__ = (
        Index(
            "uq_tags_name_active",
            "name",
            unique=True,
            postgresql_where="deleted_at IS NULL",
        ),
        Index(
            "ix_tags_normalized_name_active",
            "normalized_name",
            postgresql_where="deleted_at IS NULL",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    name: Mapped[str] = mapped_column()
    normalized_name: Mapped[str] = mapped_column(
        Computed("replace(lower(btrim(name)), ' ', '_')", persisted=True),
        init=False,
    )
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
        primaryjoin=lambda: Tag.id == pins_tags.c.tag_id,
        foreign_keys=lambda: [pins_tags.c.pin_id, pins_tags.c.tag_id],
        default_factory=set,
        back_populates="tags",
        viewonly=True,
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

    @property
    def display_name(self) -> str:
        return titlecase(self.name.replace("_", " "))

    def __hash__(self) -> int:
        return hash(self.name) + (self.id or 0)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Tag):
            return False
        return value.id == self.id

    def document(self) -> dict[str, object]:
        """Meilisearch document for tag name, display name, category, aliases."""
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
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


async def resolve_implications(
    initial: Iterable[Tag], session: AsyncSession | Session
) -> dict[Tag, Tag | None]:
    """BFS transitive closure of tag implications. Returns mapping of tag → direct source (None = explicit). Cycle-safe."""
    init_list = list(initial)
    result: dict[Tag, Tag | None] = {t: None for t in init_list}
    queue: list[tuple[Tag, Tag | None]] = [(t, None) for t in init_list]
    seen_ids: set[int] = set()
    while queue:
        tag, source = queue.pop()
        if tag.id in seen_ids:
            continue
        seen_ids.add(tag.id)
        scalars_result = session.scalars(
            select(Tag)
            .join(tag_implications, Tag.id == tag_implications.c.implied_tag_id)
            .where(tag_implications.c.tag_id == tag.id)
        )
        if isawaitable(scalars_result):
            scalars_result = await scalars_result
        typed_result = cast(ScalarResult["Tag"], scalars_result)
        implied = typed_result.all()
        for t in implied:
            if t.id not in seen_ids:
                if t not in result:
                    result[t] = tag
                queue.append((t, tag))
    return result


async def apply_pin_tags(
    pin_id: int,
    explicit_tag_ids: Iterable[int],
    session: AsyncSession | Session,
) -> None:
    """Replace all pins_tags rows for a pin. Explicit tags get NULL implied_by; implied tags get their direct source."""
    execute_result = session.execute(
        delete(pins_tags).where(pins_tags.c.pin_id == pin_id)
    )
    if isawaitable(execute_result):
        await execute_result
    explicit_tags = set(
        await _tag_scalars(
            session=session,
            statement=select(Tag).where(Tag.id.in_(list(explicit_tag_ids))),
        )
    )
    resolved = await resolve_implications(explicit_tags, session)
    for tag, source in resolved.items():
        execute_result = session.execute(
            insert(pins_tags).values(
                pin_id=pin_id,
                tag_id=tag.id,
                implied_by_tag_id=source.id if source else None,
            )
        )
        if isawaitable(execute_result):
            await execute_result


async def cascade_new_implications_to_pins(
    *,
    tag: Tag,
    newly_added_ids: set[int],
    implied_tags: Iterable[Tag],
    session: AsyncSession,
) -> None:
    """Insert implied pins_tags rows for ``tag``'s newly added implications.

    Walks the transitive closure from each newly added child and inserts a
    pins_tags row per (pin, implied_tag) pair, recording the direct source as
    ``implied_by_tag_id``. ``ON CONFLICT DO NOTHING`` keeps existing rows.
    """
    if not newly_added_ids:
        return
    newly_added_tags: list[Tag] = [
        implied_tag for implied_tag in implied_tags if implied_tag.id in newly_added_ids
    ]
    all_new_implied: dict[Tag, Tag | None] = await resolve_implications(
        initial=newly_added_tags,
        session=session,
    )
    for implied_tag, source_tag in all_new_implied.items():
        await session.execute(
            pg_insert(pins_tags)
            .from_select(
                ["pin_id", "tag_id", "implied_by_tag_id"],
                select(
                    pins_tags.c.pin_id,
                    literal(implied_tag.id).label("tag_id"),
                    literal(source_tag.id if source_tag else None).label(
                        "implied_by_tag_id"
                    ),
                ).where(pins_tags.c.tag_id == tag.id),
            )
            .on_conflict_do_nothing()
        )


async def _cascade_remove_implied(
    parent_tag_id: int, removed_child_ids: set[int], session: AsyncSession
) -> None:
    """Re-sync affected pins after implication removal. Correctly handles multi-path implications."""
    affected_pin_ids: set[int] = set()
    for child_tag_id in removed_child_ids:
        pin_ids = (
            await session.scalars(
                select(pins_tags.c.pin_id).where(
                    pins_tags.c.tag_id == child_tag_id,
                    pins_tags.c.implied_by_tag_id == parent_tag_id,
                )
            )
        ).all()
        affected_pin_ids.update(pin_ids)

    for pin_id in affected_pin_ids:
        explicit_tag_ids = (
            await session.scalars(
                select(pins_tags.c.tag_id).where(
                    pins_tags.c.pin_id == pin_id,
                    pins_tags.c.implied_by_tag_id.is_(None),
                )
            )
        ).all()
        await apply_pin_tags(pin_id, set(explicit_tag_ids), session)
