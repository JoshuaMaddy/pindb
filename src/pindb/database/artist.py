"""Artist entities with optional aliases and M2M links to pins."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from rich.repr import Result
from sqlalchemy import Computed, ForeignKey, Index, UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
    object_session,
    relationship,
)

from pindb.database._aliases import replace_aliases
from pindb.database.audit_mixin import AuditMixin
from pindb.database.base import Base
from pindb.database.joins import artists_links, pins_artists
from pindb.database.link import Link
from pindb.database.pending_mixin import PendingMixin

if TYPE_CHECKING:
    from pindb.database.pin import Pin


class ArtistAlias(MappedAsDataclass, Base):
    """Alternate searchable name for an artist (unique per artist)."""

    __tablename__ = "artist_aliases"
    __table_args__ = (
        UniqueConstraint(
            "artist_id", "alias", name="uq_artist_aliases_artist_id_alias"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id"), init=False)
    alias: Mapped[str] = mapped_column()

    def __rich_repr__(self) -> Result:
        yield "id", self.id
        yield "artist_id", self.artist_id
        yield "alias", self.alias


class Artist(PendingMixin, AuditMixin, MappedAsDataclass, Base):
    """Creator/studio attached to pins (optional description and outbound links)."""

    __tablename__ = "artists"
    __table_args__ = (Index("ix_artists_normalized_name", "normalized_name"),)

    id: Mapped[int] = mapped_column(
        primary_key=True,
        init=False,
    )

    # Required Attributes
    name: Mapped[str]
    normalized_name: Mapped[str] = mapped_column(
        Computed("replace(lower(btrim(name)), ' ', '_')", persisted=True),
        init=False,
    )

    # Optional Attributes
    description: Mapped[str | None] = mapped_column(default=None)
    active: Mapped[bool] = mapped_column(default=True)

    # Required Relationships
    pins: Mapped[set[Pin]] = relationship(
        secondary=pins_artists,
        default_factory=set,
        back_populates="artists",
    )

    aliases: Mapped[list[ArtistAlias]] = relationship(
        default_factory=list,
        cascade="all, delete-orphan",
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
            "aliases": [a.alias for a in self.aliases],
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
            yield "aliases", self.aliases, []
            yield "links", self.links, set()


async def replace_artist_aliases(
    artist: Artist, aliases: Iterable[str], session: AsyncSession
) -> None:
    """Replace persisted aliases for ``artist`` (see ``replace_tag_aliases``)."""
    await replace_aliases(
        owner=artist,
        alias_cls=ArtistAlias,
        raw_aliases=aliases,
        session=session,
    )
