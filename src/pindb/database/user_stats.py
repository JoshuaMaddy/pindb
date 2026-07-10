"""Derived per-user statistics and earned achievement tiers.

``UserStats`` is recomputed from source tables (never incremented) by
``pindb.achievements.recalculate_user_stats``; ``UserAchievement`` rows are
permanent — the unique constraint is the exactly-once award mechanism.
Neither table is audited (derived, high-churn data, like ``MessageReceipt``).
"""

from __future__ import annotations

from datetime import datetime

from rich.repr import Result
from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from pindb.database.base import Base
from pindb.utils import utc_now


class UserStats(MappedAsDataclass, Base):
    """One wide row of high-level counts per user."""

    __tablename__ = "user_stats"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    pins_created: Mapped[int] = mapped_column(default=0)
    unique_pins_edited: Mapped[int] = mapped_column(default=0)
    unique_other_pins_edited: Mapped[int] = mapped_column(default=0)
    tags_created: Mapped[int] = mapped_column(default=0)
    unique_tags_edited: Mapped[int] = mapped_column(default=0)
    unique_other_tags_edited: Mapped[int] = mapped_column(default=0)
    shops_created: Mapped[int] = mapped_column(default=0)
    unique_shops_edited: Mapped[int] = mapped_column(default=0)
    unique_other_shops_edited: Mapped[int] = mapped_column(default=0)
    artists_created: Mapped[int] = mapped_column(default=0)
    unique_artists_edited: Mapped[int] = mapped_column(default=0)
    unique_other_artists_edited: Mapped[int] = mapped_column(default=0)
    global_sets_created: Mapped[int] = mapped_column(default=0)
    pins_favorited: Mapped[int] = mapped_column(default=0)
    pins_owned: Mapped[int] = mapped_column(default=0)
    pins_wanted: Mapped[int] = mapped_column(default=0)

    updated_at: Mapped[datetime] = mapped_column(default_factory=utc_now)

    def __rich_repr__(self) -> Result:
        try:
            yield "user_id", self.user_id
            yield "pins_created", self.pins_created
            yield "unique_pins_edited", self.unique_pins_edited
            yield "unique_other_pins_edited", self.unique_other_pins_edited
            yield "tags_created", self.tags_created
            yield "unique_tags_edited", self.unique_tags_edited
            yield "unique_other_tags_edited", self.unique_other_tags_edited
            yield "shops_created", self.shops_created
            yield "unique_shops_edited", self.unique_shops_edited
            yield "unique_other_shops_edited", self.unique_other_shops_edited
            yield "artists_created", self.artists_created
            yield "unique_artists_edited", self.unique_artists_edited
            yield "unique_other_artists_edited", self.unique_other_artists_edited
            yield "global_sets_created", self.global_sets_created
            yield "pins_favorited", self.pins_favorited
            yield "pins_owned", self.pins_owned
            yield "pins_wanted", self.pins_wanted
            yield "updated_at", self.updated_at
        except Exception:
            yield "detached", True


class UserAchievement(MappedAsDataclass, Base):
    """One row per earned (user, family, tier) — never removed on stat drop."""

    __tablename__ = "user_achievements"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "family",
            "tier",
            name="uq_user_achievements_user_id_family_tier",
        ),
        Index("ix_user_achievements_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    family: Mapped[str]
    tier: Mapped[int]
    achieved_at: Mapped[datetime] = mapped_column(default_factory=utc_now, init=False)

    def __rich_repr__(self) -> Result:
        try:
            yield "id", self.id
            yield "user_id", self.user_id
            yield "family", self.family
            yield "tier", self.tier
            yield "achieved_at", self.achieved_at
        except Exception:
            yield "detached", True
