"""`/bulk/tag*` routes: form access, JSON tag creation with cross-row
implications, per-row error isolation, and bulk_id grouping for editor
submissions (admin auto-approves)."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pindb.database import Tag, TagCategory


def _row(name, category="general", **extra):
    payload = {
        "client_id": f"row-{name}",
        "name": name,
        "category": category,
        "description": None,
        "aliases": [],
        "implication_names": [],
    }
    payload.update(extra)
    return payload


@pytest.mark.integration
class TestBulkTagAuthorization:
    def test_guest_rejected(self, anon_client):
        response = anon_client.get("/bulk/tag")
        assert response.status_code in (401, 403)

    def test_regular_user_rejected(self, auth_client):
        response = auth_client.get("/bulk/tag")
        assert response.status_code == 403

    def test_editor_allowed(self, editor_client):
        response = editor_client.get("/bulk/tag")
        assert response.status_code == 200

    def test_admin_allowed(self, admin_client):
        response = admin_client.get("/bulk/tag")
        assert response.status_code == 200


@pytest.mark.integration
class TestBulkTagsCreate:
    def test_single_row_creates_tag(self, admin_client, db_session):
        response = admin_client.post(
            "/bulk/tag",
            json={"tags": [_row("Pikachu", "character")]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created_count"] == 1
        assert data["failed_count"] == 0
        assert data["results"][0]["success"] is True

        db_session.expire_all()
        tag = db_session.scalar(select(Tag).where(Tag.name == "pikachu"))
        assert tag is not None
        assert tag.category == TagCategory.character

    def test_two_rows_with_in_batch_implication(self, admin_client, db_session):
        # Row pikachu (character) implies row pokemon (copyright). Both new.
        response = admin_client.post(
            "/bulk/tag",
            json={
                "tags": [
                    _row("pikachu", "character", implication_names=["pokemon"]),
                    _row("pokemon", "copyright"),
                ]
            },
        )
        assert response.status_code == 200
        assert response.json()["created_count"] == 2

        db_session.expire_all()
        pikachu = db_session.scalar(
            select(Tag)
            .where(Tag.name == "pikachu")
            .options(selectinload(Tag.implications))
        )
        pokemon = db_session.scalar(select(Tag).where(Tag.name == "pokemon"))
        assert pikachu is not None and pokemon is not None
        assert {t.id for t in pikachu.implications} == {pokemon.id}

    def test_implication_to_existing_db_tag(self, admin_client, admin_user, db_session):
        from tests.factories.tag import TagFactory

        existing = TagFactory(
            name="nintendo",
            category=TagCategory.company,
            approved=True,
            created_by=admin_user,
        )
        assert isinstance(existing, Tag)
        db_session.flush()

        response = admin_client.post(
            "/bulk/tag",
            json={
                "tags": [_row("pokemon", "copyright", implication_names=["nintendo"])]
            },
        )
        assert response.status_code == 200
        assert response.json()["created_count"] == 1

        db_session.expire_all()
        pokemon = db_session.scalar(
            select(Tag)
            .where(Tag.name == "pokemon")
            .options(selectinload(Tag.implications))
        )
        assert pokemon is not None
        assert {t.id for t in pokemon.implications} == {existing.id}

        # No duplicate nintendo created.
        nintendos = db_session.scalars(select(Tag).where(Tag.name == "nintendo")).all()
        assert len(nintendos) == 1

    def test_aliases_persisted_and_normalized(self, admin_client, db_session):
        response = admin_client.post(
            "/bulk/tag",
            json={"tags": [_row("pokemon", aliases=["Long Form", "Pocket Monsters"])]},
        )
        assert response.status_code == 200
        assert response.json()["created_count"] == 1

        db_session.expire_all()
        pokemon = db_session.scalar(
            select(Tag).where(Tag.name == "pokemon").options(selectinload(Tag.aliases))
        )
        assert pokemon is not None
        assert {a.alias for a in pokemon.aliases} == {"long_form", "pocket_monsters"}

    def test_cycle_rejected_per_row(self, admin_client, db_session):
        response = admin_client.post(
            "/bulk/tag",
            json={
                "tags": [
                    _row("a", implication_names=["b"]),
                    _row("b", implication_names=["a"]),
                ]
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["failed_count"] == 2
        assert data["created_count"] == 0
        for result in data["results"]:
            assert result["success"] is False
            assert "cycle" in result["error"].lower()

        db_session.expire_all()
        rows = db_session.scalars(select(Tag).where(Tag.name.in_(["a", "b"]))).all()
        assert rows == []

    def test_duplicate_name_within_batch_isolated(self, admin_client, db_session):
        response = admin_client.post(
            "/bulk/tag",
            json={"tags": [_row("dup"), _row("Dup")]},  # Both normalize to "dup"
        )
        assert response.status_code == 200
        data = response.json()
        # Both rows reference the same name and must fail (we cannot pick a winner).
        assert data["failed_count"] == 2
        assert data["created_count"] == 0
        for result in data["results"]:
            assert "duplicate" in result["error"].lower()

        db_session.expire_all()
        rows = db_session.scalars(select(Tag).where(Tag.name == "dup")).all()
        assert rows == []

    def test_collision_with_existing_db_tag_isolated(
        self, admin_client, admin_user, db_session
    ):
        from tests.factories.tag import TagFactory

        TagFactory(name="taken", approved=True, created_by=admin_user)
        db_session.flush()

        response = admin_client.post(
            "/bulk/tag",
            json={"tags": [_row("taken"), _row("fresh")]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created_count"] == 1
        assert data["failed_count"] == 1
        taken_result, fresh_result = data["results"]
        assert taken_result["success"] is False
        assert fresh_result["success"] is True

        db_session.expire_all()
        fresh = db_session.scalar(select(Tag).where(Tag.name == "fresh"))
        assert fresh is not None


@pytest.mark.integration
class TestBulkTagBulkId:
    def test_editor_tags_share_bulk_id_and_stay_pending(
        self, editor_client, db_session
    ):
        response = editor_client.post(
            "/bulk/tag",
            json={
                "tags": [
                    _row("editor_one"),
                    _row("editor_two"),
                    _row("editor_three"),
                ]
            },
        )
        assert response.status_code == 200
        assert response.json()["created_count"] == 3

        db_session.expire_all()
        tags = db_session.scalars(
            select(Tag)
            .where(Tag.name.in_(["editor_one", "editor_two", "editor_three"]))
            .execution_options(include_pending=True)
        ).all()
        assert len(tags) == 3
        bulk_ids = {tag.bulk_id for tag in tags}
        assert len(bulk_ids) == 1
        assert next(iter(bulk_ids)) is not None
        assert all(tag.approved_at is None for tag in tags)

    def test_admin_tags_auto_approve(self, admin_client, db_session):
        response = admin_client.post(
            "/bulk/tag",
            json={"tags": [_row("admin_one"), _row("admin_two")]},
        )
        assert response.status_code == 200

        db_session.expire_all()
        tags = db_session.scalars(
            select(Tag).where(Tag.name.in_(["admin_one", "admin_two"]))
        ).all()
        assert len(tags) == 2
        assert all(tag.approved_at is not None for tag in tags)


@pytest.mark.integration
class TestBulkTagOptions:
    def test_options_endpoint_excludes_self(
        self, admin_client, admin_user, db_session, patch_meilisearch
    ):
        # Stub Meili to return both names; route should drop the excluded one.
        patch_meilisearch.search.return_value = {
            "hits": [
                {"name": "foo", "display_name": "Foo", "category": "general"},
                {"name": "bar", "display_name": "Bar", "category": "general"},
            ],
            "offset": 0,
            "limit": 50,
            "estimatedTotalHits": 2,
            "processingTimeMs": 1,
            "query": "",
        }

        response = admin_client.get(
            "/bulk/options/tag", params={"q": "fo", "exclude_name": "foo"}
        )
        assert response.status_code == 200
        names = [row["value"] for row in response.json()]
        assert "foo" not in names
        assert "bar" in names
