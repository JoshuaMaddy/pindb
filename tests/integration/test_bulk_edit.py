# ty: ignore[unresolved-attribute]
"""Integration tests for the bulk-edit flow.

Covers:
- admin bulk editing an artist's pins writes directly
- editor bulk editing an artist's pins writes pending edits with a shared bulk_id
- admin bulk editing search results (admin-only)
- editors rejected from search-source bulk edits
- admin reject-bulk + approve-bulk endpoints on the pending queue
"""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import select

from pindb.database.joins import pin_set_memberships, pins_artists
from pindb.database.pending_edit import PendingEdit
from pindb.database.pin import Pin
from pindb.database.tag import TagCategory
from tests.factories.artist import ArtistFactory
from tests.factories.pin import PinFactory
from tests.factories.pin_set import PinSetFactory
from tests.factories.tag import TagFactory


def _link_pin_to_artist(db_session, pin_id: int, artist_id: int) -> None:
    db_session.execute(
        pins_artists.insert().values(pin_id=pin_id, artists_id=artist_id)
    )
    db_session.flush()


def _link_pin_to_set(db_session, pin_id: int, set_id: int, position: int = 0) -> None:
    db_session.execute(
        pin_set_memberships.insert().values(
            pin_id=pin_id, set_id=set_id, position=position
        )
    )
    db_session.flush()


@pytest.mark.integration
class TestBulkEditFromArtistAsAdmin:
    def test_admin_direct_write_of_scalars_and_tags(
        self, admin_client, db_session, admin_user
    ):
        artist = ArtistFactory(approved=True, created_by=admin_user)
        tag_new = TagFactory(
            name="bulk-added-tag", category=TagCategory.general, created_by=admin_user
        )
        pins = [
            PinFactory(approved=True, created_by=admin_user),
            PinFactory(approved=True, created_by=admin_user),
        ]
        for pin in pins:
            _link_pin_to_artist(db_session, pin.id, artist.id)

        response = admin_client.post(
            "/bulk-edit/apply",
            params={"source_type": "artist", "source_id": artist.id},
            data={
                "apply_field": ["posts", "width"],
                "posts_value": "3",
                "width_value": "42.5mm",
                "tag_ids": [str(tag_new.id)],
                "tag_mode": "add",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        db_session.expire_all()
        refreshed = db_session.scalars(
            select(Pin).where(Pin.id.in_([pin.id for pin in pins]))
        ).all()
        assert {pin.posts for pin in refreshed} == {3}
        assert {pin.width for pin in refreshed} == {42.5}
        for pin in refreshed:
            assert tag_new in pin.explicit_tags

        # Admin direct writes do NOT create pending edits.
        assert db_session.scalar(select(PendingEdit).limit(1)) is None, (
            "Admin bulk edit should not create any pending edits"
        )

    def test_invalid_width_returns_400(self, admin_client, db_session, admin_user):
        artist = ArtistFactory(approved=True, created_by=admin_user)
        pin = PinFactory(approved=True, created_by=admin_user)
        _link_pin_to_artist(db_session, pin.id, artist.id)

        response = admin_client.post(
            "/bulk-edit/apply",
            params={"source_type": "artist", "source_id": artist.id},
            data={
                "apply_field": ["width"],
                "width_value": "not-valid",
                "tag_ids": [],
                "tag_mode": "add",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400


@pytest.mark.integration
class TestBulkEditFromArtistAsEditor:
    def test_editor_produces_pending_edits_with_shared_bulk_id(
        self, editor_client, db_session, editor_user, admin_user
    ):
        artist = ArtistFactory(approved=True, created_by=admin_user)
        tag_new = TagFactory(
            name="editor-added-tag",
            category=TagCategory.general,
            created_by=admin_user,
        )
        pins = [
            PinFactory(approved=True, created_by=admin_user),
            PinFactory(approved=True, created_by=admin_user),
        ]
        for pin in pins:
            _link_pin_to_artist(db_session, pin.id, artist.id)

        response = editor_client.post(
            "/bulk-edit/apply",
            params={"source_type": "artist", "source_id": artist.id},
            data={
                "apply_field": ["posts"],
                "posts_value": "4",
                "tag_ids": [str(tag_new.id)],
                "tag_mode": "add",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        db_session.expire_all()
        # Pin canonical rows untouched — change is in pending edits.
        for pin in db_session.scalars(
            select(Pin).where(Pin.id.in_([p.id for p in pins]))
        ).all():
            assert pin.posts != 4

        pending_edits = db_session.scalars(
            select(PendingEdit).where(
                PendingEdit.entity_type == "pins",
                PendingEdit.entity_id.in_([p.id for p in pins]),
            )
        ).all()
        assert len(pending_edits) == 2
        bulk_ids = {edit.bulk_id for edit in pending_edits}
        assert len(bulk_ids) == 1
        assert next(iter(bulk_ids)) is not None
        for edit in pending_edits:
            assert "posts" in edit.patch
            assert edit.patch["posts"]["new"] == 4
            assert tag_new.id in edit.patch["tag_ids"]["new"]


@pytest.mark.integration
class TestBulkEditFromSearch:
    def test_editor_blocked_from_search_source(self, editor_client):
        response = editor_client.get("/bulk-edit/from/search?q=anything")
        assert response.status_code == 403

    def test_admin_search_is_direct_write(
        self, admin_client, db_session, admin_user, patch_meilisearch
    ):
        pin_match = PinFactory(name="MatchMe", approved=True, created_by=admin_user)
        pin_skip = PinFactory(name="SkipMe", approved=True, created_by=admin_user)
        # Meili mock: only pin_match comes back for the search.
        patch_meilisearch.search.return_value = {
            "hits": [{"id": pin_match.id, "name": pin_match.name, "shops": []}],
            "offset": 0,
            "limit": 20,
            "estimatedTotalHits": 1,
            "processingTimeMs": 1,
            "query": "match",
        }

        response = admin_client.post(
            "/bulk-edit/apply",
            params={"search_query": "match"},
            data={
                "apply_field": ["posts"],
                "posts_value": "9",
                "tag_ids": [],
                "tag_mode": "add",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        db_session.expire_all()
        matched = db_session.get(Pin, pin_match.id)
        skipped = db_session.get(Pin, pin_skip.id)
        assert matched is not None and matched.posts == 9
        assert skipped is not None and skipped.posts != 9
        assert db_session.scalar(select(PendingEdit).limit(1)) is None, (
            "Search bulk edit bypasses the pending flow"
        )


@pytest.mark.integration
class TestBulkRejectionAndApproval:
    def _seed_editor_bulk(self, client, db_session, editor_user, admin_user):
        artist = ArtistFactory(approved=True, created_by=admin_user)
        tag_new = TagFactory(
            name="bundle-tag", category=TagCategory.general, created_by=admin_user
        )
        pins = [
            PinFactory(approved=True, created_by=admin_user),
            PinFactory(approved=True, created_by=admin_user),
        ]
        for pin in pins:
            _link_pin_to_artist(db_session, pin.id, artist.id)
        client.post(
            "/bulk-edit/apply",
            params={"source_type": "artist", "source_id": artist.id},
            data={
                "apply_field": ["posts"],
                "posts_value": "7",
                "tag_ids": [str(tag_new.id)],
                "tag_mode": "add",
            },
            follow_redirects=False,
        )
        db_session.expire_all()
        edits = db_session.scalars(
            select(PendingEdit).where(PendingEdit.entity_id.in_([p.id for p in pins]))
        ).all()
        return pins, edits

    def test_reject_bulk_marks_all_edits_rejected(
        self, editor_client, admin_client, db_session, editor_user, admin_user
    ):
        pins, edits = self._seed_editor_bulk(
            editor_client, db_session, editor_user, admin_user
        )
        bulk_id: UUID = edits[0].bulk_id
        assert bulk_id is not None

        response = admin_client.post(
            f"/admin/pending/reject-bulk/{bulk_id}", follow_redirects=False
        )
        assert response.status_code == 303

        db_session.expire_all()
        rejected = db_session.scalars(
            select(PendingEdit).where(PendingEdit.bulk_id == bulk_id)
        ).all()
        assert len(rejected) == 2
        for edit in rejected:
            assert edit.rejected_at is not None

    def test_approve_bulk_applies_all_edits(
        self, editor_client, admin_client, db_session, editor_user, admin_user
    ):
        pins, edits = self._seed_editor_bulk(
            editor_client, db_session, editor_user, admin_user
        )
        bulk_id: UUID = edits[0].bulk_id

        response = admin_client.post(
            f"/admin/pending/approve-bulk/{bulk_id}", follow_redirects=False
        )
        assert response.status_code == 303

        db_session.expire_all()
        for pin in db_session.scalars(
            select(Pin).where(Pin.id.in_([p.id for p in pins]))
        ).all():
            assert pin.posts == 7
        approved_edits = db_session.scalars(
            select(PendingEdit).where(PendingEdit.bulk_id == bulk_id)
        ).all()
        for edit in approved_edits:
            assert edit.approved_at is not None


@pytest.mark.integration
class TestBulkEditEntryButtons:
    def test_pin_set_page_shows_bulk_button_for_editor(
        self, editor_client, db_session, editor_user
    ):
        pin_set = PinSetFactory(approved=True, created_by=editor_user)
        response = editor_client.get(f"/get/pin_set/{pin_set.id}")
        assert response.status_code == 200
        assert f"/bulk-edit/from/pin_set/{pin_set.id}" in response.text

    def test_artist_page_shows_bulk_button_for_editor(
        self, editor_client, db_session, admin_user
    ):
        artist = ArtistFactory(approved=True, created_by=admin_user)
        response = editor_client.get(f"/get/artist/{artist.id}")
        assert response.status_code == 200
        assert f"/bulk-edit/from/artist/{artist.id}" in response.text


@pytest.mark.integration
class TestTagMode:
    def test_replace_overwrites_explicit_tags(
        self, admin_client, db_session, admin_user
    ):
        artist = ArtistFactory(approved=True, created_by=admin_user)
        old_tag = TagFactory(name="old-tag", created_by=admin_user)
        new_tag = TagFactory(name="new-tag", created_by=admin_user)
        pin = PinFactory(approved=True, created_by=admin_user)
        _link_pin_to_artist(db_session, pin.id, artist.id)
        from pindb.database.tag import apply_pin_tags

        apply_pin_tags(pin.id, [old_tag.id], db_session)
        db_session.flush()

        response = admin_client.post(
            "/bulk-edit/apply",
            params={"source_type": "artist", "source_id": artist.id},
            data={
                "apply_field": [],
                "tag_ids": [str(new_tag.id)],
                "tag_mode": "replace",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        db_session.expire_all()
        refreshed = db_session.get(Pin, pin.id)
        assert refreshed is not None
        tag_names = {t.name for t in refreshed.explicit_tags}
        assert tag_names == {"new-tag"}

    def test_remove_drops_tags_only(self, admin_client, db_session, admin_user):
        artist = ArtistFactory(approved=True, created_by=admin_user)
        keep_tag = TagFactory(name="keep-tag", created_by=admin_user)
        drop_tag = TagFactory(name="drop-tag", created_by=admin_user)
        pin = PinFactory(approved=True, created_by=admin_user)
        _link_pin_to_artist(db_session, pin.id, artist.id)
        from pindb.database.tag import apply_pin_tags

        apply_pin_tags(pin.id, [keep_tag.id, drop_tag.id], db_session)
        db_session.flush()

        response = admin_client.post(
            "/bulk-edit/apply",
            params={"source_type": "artist", "source_id": artist.id},
            data={
                "apply_field": [],
                "tag_ids": [str(drop_tag.id)],
                "tag_mode": "remove",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        db_session.expire_all()
        refreshed = db_session.get(Pin, pin.id)
        assert refreshed is not None
        assert {t.name for t in refreshed.explicit_tags} == {"keep-tag"}
