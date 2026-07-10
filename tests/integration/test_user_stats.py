"""Achievements system: stats recompute, awarding, messaging, erasure, UI.

Covers `pindb.achievements`: recompute-from-source correctness (approved /
pending / soft-deleted filtering, ChangeLog + PendingEdit edit union,
others'-entities predicate incl. NULL creators), determinism under different
audit roles, exactly-once tier awarding + achievement messages, route wiring,
account erasure cleanup, and the profile badge row.
"""

from __future__ import annotations

from typing import cast

import pytest
from sqlalchemy import insert, select

from pindb.achievements import (
    AchievementFamily,
    _award_new_achievements,
    recalculate_user_stats,
    refresh_user_stats,
)
from pindb.audit_events import set_audit_user, set_audit_user_flags
from pindb.database import (
    ChangeLog,
    Message,
    MessageCategory,
    UserAchievement,
    UserOwnedPin,
    UserStats,
    UserWantedPin,
    async_session_maker,
)
from pindb.database.joins import user_favorite_pins
from pindb.database.pin import Pin
from pindb.models.message_body import AchievementBody
from pindb.utils import utc_now
from tests.factories.pending_edit import PendingEditFactory
from tests.factories.pin import PinFactory
from tests.factories.pin_set import PinSetFactory
from tests.fixtures.users import SUBJECT_USER_PARAMS

# --- Helpers -----------------------------------------------------------------

_STAT_FIELDS: tuple[str, ...] = (
    "pins_created",
    "unique_pins_edited",
    "unique_other_pins_edited",
    "tags_created",
    "unique_tags_edited",
    "unique_other_tags_edited",
    "shops_created",
    "unique_shops_edited",
    "unique_other_shops_edited",
    "artists_created",
    "unique_artists_edited",
    "unique_other_artists_edited",
    "global_sets_created",
    "pins_favorited",
    "pins_owned",
    "pins_wanted",
)


async def _recalculate(user_id: int) -> UserStats:
    async with async_session_maker.begin() as session:
        return await recalculate_user_stats(session=session, user_id=user_id)


async def _award(user_id: int, stats: UserStats) -> None:
    async with async_session_maker.begin() as session:
        await _award_new_achievements(session=session, user_id=user_id, stats=stats)


def _stat_dict(stats: UserStats) -> dict[str, int]:
    return {field: getattr(stats, field) for field in _STAT_FIELDS}


def _achievement_rows(db_session, user_id: int) -> list[UserAchievement]:
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(UserAchievement)
            .where(UserAchievement.user_id == user_id)
            .order_by(UserAchievement.family, UserAchievement.tier)
        ).all()
    )


def _achievement_messages(db_session, user_id: int) -> list[Message]:
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(Message).where(
                Message.recipient_id == user_id,
                Message.category == MessageCategory.achievement,
            )
        ).all()
    )


# --- Recompute correctness ----------------------------------------------------


@pytest.mark.integration
class TestRecalculateUserStats:
    async def test_pins_created_counts_only_live_approved(self, db_session, test_user):
        PinFactory(created_by=test_user)
        PinFactory(created_by=test_user)
        PinFactory(created_by=test_user, approved=False)  # pending
        rejected = cast(Pin, PinFactory(created_by=test_user))
        rejected.rejected_at = utc_now()
        deleted = cast(Pin, PinFactory(created_by=test_user))
        deleted.deleted_at = utc_now()
        db_session.flush()

        stats = await _recalculate(test_user.id)
        assert stats.pins_created == 2

    async def test_edit_union_dedupes_and_others_predicate(
        self, db_session, test_user, admin_user
    ):
        pin_own = cast(Pin, PinFactory(created_by=test_user))
        pin_other = cast(Pin, PinFactory(created_by=admin_user))
        pin_anon = cast(Pin, PinFactory())  # created_by_id stays NULL
        pin_pending_edit_only = cast(Pin, PinFactory(created_by=admin_user))

        for pin in (pin_own, pin_other, pin_anon):
            db_session.add(
                ChangeLog(
                    entity_type="pins",
                    entity_id=pin.id,
                    operation="update",
                    changed_by_id=test_user.id,
                )
            )
        # Approved PendingEdit on a pin ALSO edited via ChangeLog — must dedupe.
        PendingEditFactory(
            entity_id=pin_other.id,
            created_by_id=test_user.id,
            approved_at=utc_now(),
        )
        # Unapproved PendingEdit contributes nothing.
        PendingEditFactory(
            entity_id=pin_pending_edit_only.id,
            created_by_id=test_user.id,
        )
        # Someone else's edits contribute nothing.
        db_session.add(
            ChangeLog(
                entity_type="pins",
                entity_id=pin_own.id,
                operation="update",
                changed_by_id=admin_user.id,
            )
        )
        db_session.flush()

        stats = await _recalculate(test_user.id)
        assert stats.unique_pins_edited == 3
        # NULL-creator pin counts as someone else's (IS DISTINCT FROM).
        assert stats.unique_other_pins_edited == 2

    async def test_create_operations_do_not_count_as_edits(self, db_session, test_user):
        pin = cast(Pin, PinFactory(created_by=test_user))
        db_session.add(
            ChangeLog(
                entity_type="pins",
                entity_id=pin.id,
                operation="create",
                changed_by_id=test_user.id,
            )
        )
        db_session.flush()

        stats = await _recalculate(test_user.id)
        assert stats.unique_pins_edited == 0

    async def test_global_sets_created_excludes_personal_and_pending(
        self, db_session, test_user
    ):
        PinSetFactory(created_by=test_user)  # global, approved
        PinSetFactory(created_by=test_user, owner_id=test_user.id)  # personal
        PinSetFactory(created_by=test_user, approved=False)  # global, pending
        db_session.flush()

        stats = await _recalculate(test_user.id)
        assert stats.global_sets_created == 1

    async def test_collection_counts_are_distinct_per_pin(self, db_session, test_user):
        pin_a = cast(Pin, PinFactory())
        pin_b = cast(Pin, PinFactory())

        from pindb.database.grade import Grade
        from tests.factories.grade import GradeFactory

        grade = cast(Grade, GradeFactory())
        db_session.add(
            UserOwnedPin(user_id=test_user.id, pin_id=pin_a.id, grade_id=None)
        )
        db_session.add(
            UserOwnedPin(user_id=test_user.id, pin_id=pin_a.id, grade_id=grade.id)
        )
        db_session.add(
            UserOwnedPin(user_id=test_user.id, pin_id=pin_b.id, grade_id=None)
        )
        db_session.add(
            UserWantedPin(user_id=test_user.id, pin_id=pin_a.id, grade_id=None)
        )
        db_session.execute(
            insert(user_favorite_pins).values(
                [
                    {"user_id": test_user.id, "pin_id": pin_a.id},
                    {"user_id": test_user.id, "pin_id": pin_b.id},
                ]
            )
        )
        db_session.flush()

        stats = await _recalculate(test_user.id)
        assert stats.pins_owned == 2
        assert stats.pins_wanted == 1
        assert stats.pins_favorited == 2

    async def test_recompute_is_deterministic_across_audit_roles(
        self, db_session, test_user, admin_user
    ):
        PinFactory(created_by=test_user)
        PinFactory(created_by=test_user, approved=False)
        deleted = cast(Pin, PinFactory(created_by=test_user))
        deleted.deleted_at = utc_now()
        db_session.flush()

        set_audit_user(admin_user.id)
        set_audit_user_flags(is_admin=True, is_editor=True)
        as_admin = await _recalculate(test_user.id)

        set_audit_user(None)
        set_audit_user_flags(is_admin=False, is_editor=False)
        as_guest = await _recalculate(test_user.id)

        assert _stat_dict(as_admin) == _stat_dict(as_guest)

    async def test_upsert_creates_then_updates_row(self, db_session, test_user):
        await _recalculate(test_user.id)
        PinFactory(created_by=test_user)
        db_session.flush()
        await _recalculate(test_user.id)

        db_session.expire_all()
        rows = list(
            db_session.scalars(
                select(UserStats).where(UserStats.user_id == test_user.id)
            ).all()
        )
        assert len(rows) == 1
        assert rows[0].pins_created == 1


# --- Awarding + messaging -----------------------------------------------------


@pytest.mark.integration
class TestAwarding:
    async def test_tiers_awarded_once_with_exactly_one_message_each(
        self, db_session, test_user
    ):
        await _award(test_user.id, UserStats(user_id=test_user.id, pins_owned=25))

        rows = _achievement_rows(db_session, test_user.id)
        assert [(row.family, row.tier) for row in rows] == [
            (AchievementFamily.hoarder.value, 1),
            (AchievementFamily.hoarder.value, 2),
        ]
        assert len(_achievement_messages(db_session, test_user.id)) == 2

        # Re-running with the same stats awards nothing new.
        await _award(test_user.id, UserStats(user_id=test_user.id, pins_owned=25))
        assert len(_achievement_rows(db_session, test_user.id)) == 2
        assert len(_achievement_messages(db_session, test_user.id)) == 2

        # Crossing higher thresholds awards only the new tiers.
        await _award(test_user.id, UserStats(user_id=test_user.id, pins_owned=100))
        assert len(_achievement_rows(db_session, test_user.id)) == 4
        assert len(_achievement_messages(db_session, test_user.id)) == 4

        # Dropping below thresholds never removes earned tiers.
        await _award(test_user.id, UserStats(user_id=test_user.id, pins_owned=3))
        assert len(_achievement_rows(db_session, test_user.id)) == 4
        assert len(_achievement_messages(db_session, test_user.id)) == 4

    async def test_message_shape_round_trips_as_achievement_body(
        self, db_session, test_user
    ):
        await _award(test_user.id, UserStats(user_id=test_user.id, pins_owned=10))

        (message,) = _achievement_messages(db_session, test_user.id)
        assert message.sender_id is None
        assert message.category == MessageCategory.achievement
        # PydanticJSON round-trips the discriminated union back to the model.
        body = message.body
        assert isinstance(body, AchievementBody)
        assert body.family == AchievementFamily.hoarder.value
        assert body.tier == 1
        assert body.name == "Bronze Hoarder"
        assert body.threshold == 10

    async def test_single_tier_family_uses_bare_name(self, db_session, test_user):
        await _award(test_user.id, UserStats(user_id=test_user.id, pins_favorited=150))

        rows = _achievement_rows(db_session, test_user.id)
        assert [(row.family, row.tier) for row in rows] == [
            (AchievementFamily.pin_lover.value, 1),
        ]
        (message,) = _achievement_messages(db_session, test_user.id)
        assert isinstance(message.body, AchievementBody)
        assert message.body.name == "Pin Lover"

    async def test_refresh_user_stats_end_to_end(self, db_session, test_user):
        for _ in range(10):
            PinFactory(created_by=test_user)
        db_session.flush()

        await refresh_user_stats(user_id=test_user.id)

        db_session.expire_all()
        stats = db_session.scalars(
            select(UserStats).where(UserStats.user_id == test_user.id)
        ).one()
        assert stats.pins_created == 10
        rows = _achievement_rows(db_session, test_user.id)
        assert (AchievementFamily.pinsmith.value, 1) in [
            (row.family, row.tier) for row in rows
        ]
        assert len(_achievement_messages(db_session, test_user.id)) == 1


# --- Route wiring ---------------------------------------------------------------


@pytest.mark.integration
class TestRouteWiring:
    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS[:1], indirect=True)
    def test_add_owned_pin_refreshes_stats(
        self, auth_client_as_subject, db_session, subject_user
    ):
        pin = cast(Pin, PinFactory())
        response = auth_client_as_subject.post(
            f"/user/pins/{pin.id}/owned",
            data={"quantity": "1"},
        )
        assert response.status_code == 204

        db_session.expire_all()
        stats = db_session.scalars(
            select(UserStats).where(UserStats.user_id == subject_user.id)
        ).one()
        assert stats.pins_owned == 1


# --- Erasure --------------------------------------------------------------------


@pytest.mark.integration
class TestErasure:
    async def test_erasure_removes_stats_and_achievements(self, db_session, test_user):
        from pindb.database.erasure import erase_user_account

        await _award(test_user.id, UserStats(user_id=test_user.id, pins_owned=10))
        await _recalculate(test_user.id)
        assert _achievement_rows(db_session, test_user.id)

        user_id = test_user.id
        async with async_session_maker.begin() as session:
            await erase_user_account(session, user_id)

        db_session.expire_all()
        assert (
            db_session.scalars(
                select(UserStats).where(UserStats.user_id == user_id)
            ).first()
            is None
        )
        assert _achievement_rows(db_session, user_id) == []


# --- Profile badge row -----------------------------------------------------------


@pytest.mark.integration
class TestProfileBadges:
    def test_profile_shows_only_highest_tier_per_family(
        self, client, db_session, test_user
    ):
        db_session.add(
            UserAchievement(
                user_id=test_user.id,
                family=AchievementFamily.hoarder.value,
                tier=1,
            )
        )
        db_session.add(
            UserAchievement(
                user_id=test_user.id,
                family=AchievementFamily.hoarder.value,
                tier=2,
            )
        )
        db_session.add(
            UserAchievement(
                user_id=test_user.id,
                family=AchievementFamily.pin_lover.value,
                tier=1,
            )
        )
        db_session.flush()

        response = client.get(f"/user/{test_user.username}")
        assert response.status_code == 200
        html = response.text
        assert "Silver Hoarder (II)" in html
        assert "Bronze Hoarder" not in html
        assert "Pin Lover" in html

    def test_profile_without_achievements_has_no_badge_row(
        self, client, db_session, test_user
    ):
        response = client.get(f"/user/{test_user.username}")
        assert response.status_code == 200
        assert "achievement-badge" not in response.text
