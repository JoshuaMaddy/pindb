"""Tag implication closure, alias uniqueness, and `apply_pin_tags` behaviour."""

from __future__ import annotations

from typing import cast

import pytest
from sqlalchemy import select

from pindb.database import Tag
from pindb.database.joins import pins_tags
from pindb.database.tag import (
    apply_pin_tags,
    normalize_tag_name,
    replace_tag_aliases,
    resolve_implications,
)
from tests.factories.pin import PinFactory
from tests.factories.tag import TagFactory


@pytest.mark.integration
class TestTagNormalization:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Rare Pin", "rare_pin"),
            ("   spaced out   ", "spaced_out"),
            ("MIXED Case", "mixed_case"),
            ("already_snake", "already_snake"),
        ],
    )
    def test_normalize(self, raw, expected):
        assert normalize_tag_name(raw) == expected


@pytest.mark.integration
class TestTagAliases:
    def test_aliases_persisted_by_factory(self, db_session, admin_user):
        tag = TagFactory(
            name="main_tag",
            approved=True,
            created_by=admin_user,
            aliases=["synonym", "nickname"],
        )
        db_session.flush()
        db_session.expire_all()
        refreshed = db_session.get(Tag, tag.id)  # ty:ignore[unresolved-attribute]
        assert refreshed is not None
        assert {a.alias for a in refreshed.aliases} == {"synonym", "nickname"}

    async def test_replace_tag_aliases_keeps_same_strings_without_conflict(
        self, db_session, admin_user
    ):
        """Regression: re-saving unchanged aliases must not hit uq_tag_aliases_tag_id_alias."""
        tag = cast(
            Tag,
            TagFactory(
                name="jigglypuff_alias_test",
                approved=True,
                created_by=admin_user,
                aliases=["pippi", "piepi"],
            ),
        )
        db_session.flush()
        await replace_tag_aliases(
            tag=tag,
            aliases=["pippi", "piepi", "ピッピ"],
            session=db_session,
        )
        db_session.flush()
        assert {a.alias for a in tag.aliases} == {"pippi", "piepi", "ピッピ"}

    def test_two_tags_may_use_the_same_alias_string(self, db_session, admin_user):
        t1 = cast(
            Tag,
            TagFactory(
                name="eevee_a",
                approved=True,
                created_by=admin_user,
                aliases=["goupix"],
            ),
        )
        t2 = cast(
            Tag,
            TagFactory(
                name="flareon_b",
                approved=True,
                created_by=admin_user,
                aliases=["goupix"],
            ),
        )
        db_session.flush()
        assert {a.alias for a in t1.aliases} == {"goupix"}
        assert {a.alias for a in t2.aliases} == {"goupix"}


@pytest.mark.integration
class TestImplicationClosure:
    async def test_transitive_closure_follows_chain(self, db_session, admin_user):
        """a → b → c: resolving from {a} yields {a, b, c}."""
        tag_a = TagFactory(name="a", approved=True, created_by=admin_user)
        tag_b = TagFactory(name="b", approved=True, created_by=admin_user)
        tag_c = TagFactory(name="c", approved=True, created_by=admin_user)
        tag_a.implications = {tag_b}  # ty:ignore[unresolved-attribute]
        tag_b.implications = {tag_c}  # ty:ignore[unresolved-attribute]
        db_session.flush()

        resolved = await resolve_implications([tag_a], db_session)  # ty:ignore[invalid-argument-type]
        assert {t.name for t in resolved} == {"a", "b", "c"}
        # Source tracking: a is explicit (None), b implied by a, c implied by b.
        sources = {t.name: (src.name if src else None) for t, src in resolved.items()}
        assert sources == {"a": None, "b": "a", "c": "b"}

    async def test_cycle_is_safe(self, db_session, admin_user):
        """a → b → a must not infinite-loop."""
        tag_a = TagFactory(name="a", approved=True, created_by=admin_user)
        tag_b = TagFactory(name="b", approved=True, created_by=admin_user)
        tag_a.implications = {tag_b}  # ty:ignore[unresolved-attribute]
        tag_b.implications = {tag_a}  # ty:ignore[unresolved-attribute]
        db_session.flush()

        resolved = await resolve_implications([tag_a], db_session)  # ty:ignore[invalid-argument-type]
        assert {t.name for t in resolved} == {"a", "b"}


@pytest.mark.integration
class TestApplyPinTags:
    async def test_explicit_and_implied_rows_written(self, db_session, admin_user):
        pin = PinFactory(approved=True, created_by=admin_user)
        db_session.flush()

        parent = TagFactory(name="parent", approved=True, created_by=admin_user)
        child = TagFactory(name="child", approved=True, created_by=admin_user)
        parent.implications = {child}  # ty:ignore[unresolved-attribute]
        db_session.flush()

        await apply_pin_tags(pin.id, {parent.id}, db_session)  # ty:ignore[unresolved-attribute]
        db_session.flush()

        rows = db_session.execute(
            select(pins_tags.c.tag_id, pins_tags.c.implied_by_tag_id).where(
                pins_tags.c.pin_id == pin.id  # ty:ignore[unresolved-attribute]
            )
        ).all()
        by_tag = {tag_id: implied_by for tag_id, implied_by in rows}
        assert by_tag.keys() == {parent.id, child.id}  # ty:ignore[unresolved-attribute]
        assert by_tag[parent.id] is None  # explicit  # ty:ignore[unresolved-attribute]
        assert by_tag[child.id] == parent.id  # ty:ignore[unresolved-attribute]

    async def test_reapplying_replaces_previous_rows(self, db_session, admin_user):
        pin = PinFactory(approved=True, created_by=admin_user)
        tag_one = TagFactory(name="first", approved=True, created_by=admin_user)
        tag_two = TagFactory(name="second", approved=True, created_by=admin_user)
        db_session.flush()

        await apply_pin_tags(pin.id, {tag_one.id}, db_session)  # ty:ignore[unresolved-attribute]
        db_session.flush()
        await apply_pin_tags(pin.id, {tag_two.id}, db_session)  # ty:ignore[unresolved-attribute]
        db_session.flush()

        rows = (
            db_session.execute(
                select(pins_tags.c.tag_id).where(pins_tags.c.pin_id == pin.id)  # ty:ignore[unresolved-attribute]
            )
            .scalars()
            .all()
        )
        assert set(rows) == {tag_two.id}  # ty:ignore[unresolved-attribute]
