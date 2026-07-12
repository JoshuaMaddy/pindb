"""Tests for ``database.pin_previews`` — the list-card pin counts and thumbnails.

The counts these produce used to come from ``len(tag.pins)`` on an eagerly loaded
relationship, which meant ``audit_events._filter_deleted`` applied to them for
free. ``load_pin_previews`` builds its own queries, so the thing worth testing is
that the filter still reaches them: a soft-deleted pin must not be counted or
drawn, and an unapproved one must be invisible to guests while staying visible to
editors (who are the ones expected to act on it).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import cast

import pytest

from pindb.database.joins import pins_tags
from pindb.database.pin import Pin
from pindb.database.tag import Tag
from tests.factories.pin import PinFactory
from tests.factories.tag import TagFactory


def _attach(db_session, tag: Tag, *pins: Pin) -> None:
    for pin in pins:
        db_session.execute(pins_tags.insert().values(pin_id=pin.id, tag_id=tag.id))
    db_session.flush()


def _count_badge(html: str, tag: Tag) -> str:
    """The ``(n)`` the card prints beside the tag's name.

    Anchors on ``display_name`` (what the card actually shows) and takes the last
    occurrence — the raw name also appears earlier in the card's href.
    """
    _, _, after = html.rpartition(tag.display_name)
    start = after.index("(")
    return after[start : after.index(")", start) + 1]


@pytest.mark.integration
class TestPinPreviewCounts:
    def test_soft_deleted_pins_are_not_counted(
        self,
        anon_client,
        db_session,
        admin_user,
    ):
        tag = cast(
            Tag,
            TagFactory(name="deleted_pin_tag", approved=True, created_by=admin_user),
        )
        live = cast(
            Pin, PinFactory(name="Live Pin", approved=True, created_by=admin_user)
        )
        gone = cast(
            Pin, PinFactory(name="Gone Pin", approved=True, created_by=admin_user)
        )
        gone.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        gone.deleted_by_id = admin_user.id
        _attach(db_session, tag, live, gone)

        response = anon_client.get("/list/tags?view=detailed")

        assert response.status_code == 200
        assert _count_badge(response.text, tag) == "(1)"
        assert "Gone Pin" not in response.text

    def test_pending_pins_are_hidden_from_guests(
        self,
        anon_client,
        db_session,
        admin_user,
        editor_user,
    ):
        tag = cast(
            Tag,
            TagFactory(name="pending_pin_tag", approved=True, created_by=admin_user),
        )
        approved = cast(
            Pin, PinFactory(name="Approved Pin", approved=True, created_by=admin_user)
        )
        pending = cast(
            Pin, PinFactory(name="Pending Pin", approved=False, created_by=editor_user)
        )
        _attach(db_session, tag, approved, pending)

        response = anon_client.get("/list/tags?view=detailed")

        assert response.status_code == 200
        assert _count_badge(response.text, tag) == "(1)"

    def test_pending_pins_are_counted_for_editors(
        self,
        editor_client,
        db_session,
        admin_user,
        editor_user,
    ):
        tag = cast(
            Tag,
            TagFactory(name="editor_view_tag", approved=True, created_by=admin_user),
        )
        approved = cast(
            Pin,
            PinFactory(name="Editor Approved", approved=True, created_by=admin_user),
        )
        pending = cast(
            Pin,
            PinFactory(name="Editor Pending", approved=False, created_by=editor_user),
        )
        _attach(db_session, tag, approved, pending)

        response = editor_client.get("/list/tags?view=detailed")

        assert response.status_code == 200
        assert _count_badge(response.text, tag) == "(2)"

    def test_count_is_total_while_thumbnails_are_capped_at_four(
        self,
        anon_client,
        db_session,
        admin_user,
    ):
        tag = cast(
            Tag, TagFactory(name="many_pin_tag", approved=True, created_by=admin_user)
        )
        pins = [
            cast(
                Pin,
                PinFactory(
                    name=f"Sampled Pin {index}", approved=True, created_by=admin_user
                ),
            )
            for index in range(7)
        ]
        _attach(db_session, tag, *pins)

        response = anon_client.get("/list/tags")

        assert response.status_code == 200
        assert _count_badge(response.text, tag) == "(7)"
        drawn = sum(
            f"Image of pin Sampled Pin {index}" in response.text for index in range(7)
        )
        assert drawn == 4

    def test_tag_with_no_pins_renders_zero(self, anon_client, admin_user):
        tag = cast(
            Tag, TagFactory(name="lonely_tag", approved=True, created_by=admin_user)
        )

        response = anon_client.get("/list/tags?view=detailed")

        assert response.status_code == 200
        assert _count_badge(response.text, tag) == "(0)"
