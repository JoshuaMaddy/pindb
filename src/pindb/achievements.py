"""Per-user statistics and achievement awarding.

Derived-state sync layer, analogous to ``pindb.search.update``: user stats are
always recomputed from source tables (idempotent, self-healing — survives soft
deletes, pending approval flips, GDPR erasure, and bulk imports), never
incremented. Routes call :func:`refresh_user_stats` after their write session
closes (same discipline as ``sync_entity``); a scheduler sweep
(:func:`refresh_all_user_stats`) heals any missed call site.

Awarding is exactly-once per ``(user, family, tier)``: the insert races through
``ON CONFLICT DO NOTHING ... RETURNING`` on the unique constraint, and only the
winning transaction creates the notification ``Message`` (same transaction, so
a crash rolls back both together). Achievement rows are permanent — dropping
back below a threshold never removes them.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum, auto

from sqlalchemy import Select, func, select, union
from sqlalchemy.dialects.postgresql import Insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from pindb.database import (
    Artist,
    ChangeLog,
    Message,
    MessageCategory,
    PendingEdit,
    Pin,
    PinSet,
    Shop,
    Tag,
    User,
    UserAchievement,
    UserStats,
    async_session_maker,
)
from pindb.database.user_pin_queries import (
    count_favorites,
    count_owned,
    count_wanted,
)
from pindb.models.message_body import AchievementBody
from pindb.utils import utc_now

LOGGER: logging.Logger = logging.getLogger(name="pindb.achievements")


class AchievementFamily(StrEnum):
    """Badge families; values are stored in ``user_achievements.family``."""

    pinsmith = auto()
    polisher = auto()
    taxonomist = auto()
    archivist = auto()
    merchant = auto()
    appraiser = auto()
    patron = auto()
    restorer = auto()
    curator = auto()
    pin_lover = auto()
    hoarder = auto()
    hunter = auto()


@dataclass(frozen=True)
class FamilySpec:
    """Static definition of one badge family."""

    family: AchievementFamily
    display_name: str
    stat_field: str
    icon: str
    thresholds: tuple[int, ...]
    unit_label: str


DEFAULT_THRESHOLDS: tuple[int, ...] = (10, 20, 50, 100)
TIER_NUMERALS: tuple[str, ...] = ("I", "II", "III", "IV")
TIER_METALS: tuple[str, ...] = ("bronze", "silver", "gold", "platinum")

FAMILY_SPECS: dict[AchievementFamily, FamilySpec] = {
    spec.family: spec
    for spec in (
        FamilySpec(
            family=AchievementFamily.pinsmith,
            display_name="Pinsmith",
            stat_field="pins_created",
            icon="anvil",
            thresholds=DEFAULT_THRESHOLDS,
            unit_label="pins created",
        ),
        FamilySpec(
            family=AchievementFamily.polisher,
            display_name="Polisher",
            stat_field="unique_other_pins_edited",
            icon="sparkles",
            thresholds=DEFAULT_THRESHOLDS,
            unit_label="other collectors' pins improved",
        ),
        FamilySpec(
            family=AchievementFamily.taxonomist,
            display_name="Taxonomist",
            stat_field="tags_created",
            icon="tags",
            thresholds=DEFAULT_THRESHOLDS,
            unit_label="tags created",
        ),
        FamilySpec(
            family=AchievementFamily.archivist,
            display_name="Archivist",
            stat_field="unique_other_tags_edited",
            icon="bookmark-check",
            thresholds=DEFAULT_THRESHOLDS,
            unit_label="other collectors' tags improved",
        ),
        FamilySpec(
            family=AchievementFamily.merchant,
            display_name="Merchant",
            stat_field="shops_created",
            icon="store",
            thresholds=DEFAULT_THRESHOLDS,
            unit_label="shops created",
        ),
        FamilySpec(
            family=AchievementFamily.appraiser,
            display_name="Appraiser",
            stat_field="unique_other_shops_edited",
            icon="scale",
            thresholds=DEFAULT_THRESHOLDS,
            unit_label="other collectors' shops improved",
        ),
        FamilySpec(
            family=AchievementFamily.patron,
            display_name="Patron",
            stat_field="artists_created",
            icon="palette",
            thresholds=DEFAULT_THRESHOLDS,
            unit_label="artists created",
        ),
        FamilySpec(
            family=AchievementFamily.restorer,
            display_name="Restorer",
            stat_field="unique_other_artists_edited",
            icon="brush",
            thresholds=DEFAULT_THRESHOLDS,
            unit_label="other collectors' artists improved",
        ),
        FamilySpec(
            family=AchievementFamily.curator,
            display_name="Curator",
            stat_field="global_sets_created",
            icon="library-big",
            thresholds=DEFAULT_THRESHOLDS,
            unit_label="global pin sets created",
        ),
        FamilySpec(
            family=AchievementFamily.pin_lover,
            display_name="Pin Lover",
            stat_field="pins_favorited",
            icon="heart",
            thresholds=(100,),
            unit_label="pins favorited",
        ),
        FamilySpec(
            family=AchievementFamily.hoarder,
            display_name="Hoarder",
            stat_field="pins_owned",
            icon="boxes",
            thresholds=DEFAULT_THRESHOLDS,
            unit_label="pins owned",
        ),
        FamilySpec(
            family=AchievementFamily.hunter,
            display_name="Hunter",
            stat_field="pins_wanted",
            icon="crosshair",
            thresholds=DEFAULT_THRESHOLDS,
            unit_label="pins wanted",
        ),
    )
}

# Entity models whose created/edited counts feed UserStats. Keys are the
# UserStats column prefixes ("pin" -> pins_created / unique_pins_edited / ...).
_STAT_ENTITY_MODELS: dict[str, type[Pin] | type[Tag] | type[Shop] | type[Artist]] = {
    "pin": Pin,
    "tag": Tag,
    "shop": Shop,
    "artist": Artist,
}


def tier_display_name(
    spec: FamilySpec,
    tier: int,
) -> str:
    """Return the tier's full name, e.g. ``"Gold Hoarder"``.

    Single-tier families (Pin Lover) use the bare family name.
    """
    if len(spec.thresholds) == 1:
        return spec.display_name
    return f"{TIER_METALS[tier - 1].title()} {spec.display_name}"


def tier_tooltip(
    spec: FamilySpec,
    tier: int,
) -> str:
    """Return hover text, e.g. ``"Gold Hoarder (III) — 50+ pins owned"``."""
    name: str = tier_display_name(spec=spec, tier=tier)
    if len(spec.thresholds) > 1:
        name = f"{name} ({TIER_NUMERALS[tier - 1]})"
    return f"{name} — {spec.thresholds[tier - 1]}+ {spec.unit_label}"


async def _count_created(
    session: AsyncSession,
    model: type[Pin] | type[Tag] | type[Shop] | type[Artist],
    user_id: int,
) -> int:
    """Count live, approved entities created by the user.

    Disables the role-dependent ``do_orm_execute`` filters so results are
    identical for any caller (route user, admin, or the scheduler), then
    applies the public-visibility predicates explicitly.
    """
    statement: Select[tuple[int]] = (
        select(func.count())
        .select_from(model)
        .where(
            model.created_by_id == user_id,
            model.deleted_at.is_(None),
            model.approved_at.is_not(None),
            model.rejected_at.is_(None),
        )
        .execution_options(
            include_deleted=True,
            include_pending=True,
        )
    )
    return await session.scalar(statement) or 0


async def _count_unique_edited(
    session: AsyncSession,
    model: type[Pin] | type[Tag] | type[Shop] | type[Artist],
    user_id: int,
    others_only: bool,
) -> int:
    """Count distinct entities of one type the user has edited.

    Unions two sources: direct edits recorded in ``ChangeLog`` (admins and
    owners of pending entities) and approved ``PendingEdit`` rows (editor
    edits to approved entities — the ChangeLog row for those credits the
    approving admin, so PendingEdit is the editor's paper trail). Edits to
    since-deleted entities still count; they were real contributions.

    Args:
        others_only: Restrict to entities the user did not create.
            ``IS DISTINCT FROM`` keeps entities whose creator was anonymized
            to NULL by account erasure (plain ``!=`` would drop them).
    """
    change_log_arm: Select[tuple[int]] = select(ChangeLog.entity_id).where(
        ChangeLog.entity_type == model.__tablename__,
        ChangeLog.operation == "update",
        ChangeLog.changed_by_id == user_id,
    )
    pending_edit_arm: Select[tuple[int]] = select(PendingEdit.entity_id).where(
        PendingEdit.entity_type == model.__tablename__,
        PendingEdit.created_by_id == user_id,
        PendingEdit.approved_at.is_not(None),
    )
    if others_only:
        change_log_arm = change_log_arm.join(
            model,
            ChangeLog.entity_id == model.id,
        ).where(model.created_by_id.is_distinct_from(user_id))
        pending_edit_arm = pending_edit_arm.join(
            model,
            PendingEdit.entity_id == model.id,
        ).where(model.created_by_id.is_distinct_from(user_id))

    edited_ids = union(change_log_arm, pending_edit_arm).subquery()
    statement: Select[tuple[int]] = (
        select(func.count())
        .select_from(edited_ids)
        .execution_options(
            include_deleted=True,
            include_pending=True,
        )
    )
    return await session.scalar(statement) or 0


async def _count_global_sets_created(
    session: AsyncSession,
    user_id: int,
) -> int:
    """Count live, approved global (curated) sets the user created.

    Includes personal sets later promoted to global — promotion is an
    editorial endorsement of the creator's work.
    """
    statement: Select[tuple[int]] = (
        select(func.count())
        .select_from(PinSet)
        .where(
            PinSet.owner_id.is_(None),
            PinSet.created_by_id == user_id,
            PinSet.deleted_at.is_(None),
            PinSet.approved_at.is_not(None),
            PinSet.rejected_at.is_(None),
        )
        .execution_options(
            include_deleted=True,
            include_pending=True,
        )
    )
    return await session.scalar(statement) or 0


async def recalculate_user_stats(
    session: AsyncSession,
    user_id: int,
) -> UserStats:
    """Recompute every stat for one user from source tables and upsert.

    Returns:
        UserStats: Transient snapshot of the freshly computed values (not
        attached to the session; the row itself is written via upsert).
    """
    values: dict[str, int] = {}
    for prefix, model in _STAT_ENTITY_MODELS.items():
        values[f"{prefix}s_created"] = await _count_created(
            session=session,
            model=model,
            user_id=user_id,
        )
        values[f"unique_{prefix}s_edited"] = await _count_unique_edited(
            session=session,
            model=model,
            user_id=user_id,
            others_only=False,
        )
        values[f"unique_other_{prefix}s_edited"] = await _count_unique_edited(
            session=session,
            model=model,
            user_id=user_id,
            others_only=True,
        )

    values["global_sets_created"] = await _count_global_sets_created(
        session=session,
        user_id=user_id,
    )
    values["pins_favorited"] = await count_favorites(
        session=session,
        user_id=user_id,
    )
    values["pins_owned"] = await count_owned(
        session=session,
        user_id=user_id,
    )
    values["pins_wanted"] = await count_wanted(
        session=session,
        user_id=user_id,
    )

    now = utc_now()
    upsert: Insert = pg_insert(UserStats).values(
        user_id=user_id,
        updated_at=now,
        **values,
    )
    upsert = upsert.on_conflict_do_update(
        index_elements=["user_id"],
        set_={**values, "updated_at": now},
    )
    await session.execute(upsert)

    return UserStats(
        user_id=user_id,
        updated_at=now,
        **values,
    )


async def _award_new_achievements(
    session: AsyncSession,
    user_id: int,
    stats: UserStats,
) -> None:
    """Insert newly earned achievement tiers and message the user once each.

    ``ON CONFLICT DO NOTHING ... RETURNING`` on the unique constraint decides
    the winner under concurrency: only the transaction whose insert returns a
    row creates the Message, and both share this session's transaction.
    """
    for spec in FAMILY_SPECS.values():
        stat_value: int = getattr(stats, spec.stat_field)
        for tier, threshold in enumerate(spec.thresholds, start=1):
            if stat_value < threshold:
                break

            insert_statement = (
                pg_insert(UserAchievement)
                .values(
                    user_id=user_id,
                    family=spec.family.value,
                    tier=tier,
                    achieved_at=utc_now(),
                )
                .on_conflict_do_nothing(
                    constraint="uq_user_achievements_user_id_family_tier",
                )
                .returning(UserAchievement.id)
            )
            won_insert: int | None = (
                await session.execute(insert_statement)
            ).scalar_one_or_none()
            if won_insert is None:
                continue

            # Message.created_by_id will reflect whoever triggered this
            # refresh (e.g. an approving admin) via the audit ContextVars;
            # sender_id=None is what marks it as a system message.
            session.add(
                Message(
                    category=MessageCategory.achievement,
                    body=AchievementBody(
                        family=spec.family.value,
                        tier=tier,
                        name=tier_display_name(spec=spec, tier=tier),
                        threshold=threshold,
                        unit_label=spec.unit_label,
                    ),
                    recipient_id=user_id,
                )
            )


async def refresh_user_stats(user_id: int) -> None:
    """Recompute one user's stats and award any newly earned achievements.

    Call AFTER the triggering write session closes (same discipline as
    ``sync_entity``). Never raises: a stats hiccup must not fail the route
    that triggered it, and the scheduler sweep self-heals missed refreshes.
    """
    try:
        async with async_session_maker.begin() as session:
            stats: UserStats = await recalculate_user_stats(
                session=session,
                user_id=user_id,
            )
            await _award_new_achievements(
                session=session,
                user_id=user_id,
                stats=stats,
            )
    except Exception:
        LOGGER.exception("Failed to refresh stats for user %s", user_id)


async def refresh_users_stats(user_ids: Iterable[int | None]) -> None:
    """Refresh several users' stats, ignoring ``None`` and duplicates.

    Convenience for approval flows that touch entities and edits from a mix
    of creators.
    """
    for user_id in {user_id for user_id in user_ids if user_id is not None}:
        await refresh_user_stats(user_id=user_id)


async def refresh_all_user_stats() -> None:
    """Scheduler sweep: refresh stats and achievements for every live user."""
    async with async_session_maker() as session:
        user_ids: list[int] = list(await session.scalars(select(User.id)))

    LOGGER.info("Refreshing stats for %s users", len(user_ids))
    for user_id in user_ids:
        await refresh_user_stats(user_id=user_id)
