"""Names Shops/Artists asked us not to index — the do-not-catalog blacklist.

One row per blocked name string; a real-world entity with several known
spellings/aliases gets several rows. ``normalized_name`` is the same generated
column expression Shops/Artists use, so exact comparisons share one canon.

Deliberately **not** an :class:`AuditMixin` entity — like ``ContentReport``, it
is admin-managed operational state, hard-deleted on removal, with nothing for
the soft-delete/pending loader filters to say about it.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum, auto

from rich.repr import Result
from sqlalchemy import Computed, ForeignKey, Index, Text
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from pindb.database.base import Base
from pindb.utils import utc_now

# See user_display.py: ``native_enum=False`` otherwise sizes the VARCHAR to the
# longest value present today, so the first new member needs a migration.
_ENUM_LENGTH: int = 32


class BlacklistEntityType(StrEnum):
    """Entity kinds a blacklisted name can apply to.

    Kept separate from ``database/entity_type.py::EntityType``, which is tied
    to the Meilisearch index map — a blacklist entry is never indexed.
    """

    shop = auto()
    artist = auto()


class BlacklistedName(MappedAsDataclass, Base):
    """One name that must not be cataloged as a Shop/Artist, at their request."""

    __tablename__ = "blacklisted_names"
    __table_args__ = (
        Index(
            "uq_blacklisted_names_entity_type_normalized_name",
            "entity_type",
            "normalized_name",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    entity_type: Mapped[BlacklistEntityType] = mapped_column(
        SQLAlchemyEnum(
            BlacklistEntityType,
            name="blacklistentitytype",
            native_enum=False,
            length=_ENUM_LENGTH,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
    )
    name: Mapped[str] = mapped_column(Text)
    normalized_name: Mapped[str] = mapped_column(
        Text,
        Computed("replace(lower(btrim(name)), ' ', '_')", persisted=True),
        init=False,
    )

    # Admin-facing context only ("requested via email 2026-07-01"); never shown
    # to editors — the inline warning carries a fixed message.
    reason: Mapped[str | None] = mapped_column(Text, default=None)

    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        default_factory=utc_now,
        init=False,
    )

    def __rich_repr__(self) -> Result:
        try:
            yield "id", self.id
            yield "entity_type", self.entity_type
            yield "name", self.name
            yield "reason", self.reason, None
            yield "created_at", self.created_at
        except Exception:
            yield "detached", True
