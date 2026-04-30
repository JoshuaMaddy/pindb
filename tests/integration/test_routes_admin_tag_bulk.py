"""Integration coverage for ``/admin/tags/bulk`` and ``/admin/tags/bulk-upsert``."""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pindb.database import Tag
from tests.factories.tag import TagFactory
from tests.integration.helpers.authz import assert_admin_only_get


@pytest.mark.integration
class TestAdminBulkTagsPage:
    def test_bulk_tags_page_requires_admin(self, client, auth_client, editor_client):
        assert_admin_only_get("/admin/tags/bulk", client, auth_client, editor_client)

    def test_admin_returns_200(self, admin_client):
        response = admin_client.get("/admin/tags/bulk")
        assert response.status_code == 200
        assert "Bulk tags" in response.text


@pytest.mark.integration
class TestAdminBulkTagUpsert:
    """JSON bulk-upsert: session-level dedupe skips re-fetch/re-merge for repeated names."""

    def test_shared_tag_across_roots_gets_second_pass_implications(
        self, admin_client, db_session
    ):
        u = uuid.uuid4().hex[:10]
        shared = f"bulk_shared_{u}"
        extra = f"bulk_extra_{u}"
        payload = {
            "tags": [
                {"name": f"bulk_root_a_{u}", "implications": [{"name": shared}]},
                {
                    "name": f"bulk_root_b_{u}",
                    "implications": [
                        {"name": shared, "implications": [{"name": extra}]}
                    ],
                },
            ],
        }
        response = admin_client.post("/admin/tags/bulk-upsert", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["root_tag_ids"] and len(data["touched_tag_ids"]) >= 1

        db_session.expire_all()
        tag = db_session.scalar(
            select(Tag)
            .where(Tag.name == shared)
            .options(selectinload(Tag.implications))
        )
        assert tag is not None
        implied_names = {t.name for t in tag.implications}
        assert implied_names == {extra}


@pytest.mark.integration
class TestAdminBulkTagFormRoute:
    def test_bulk_form_requires_single_input_source(self, admin_client):
        response = admin_client.post(
            "/admin/tags/bulk",
            data={"json_text": '{"name":"tag_a"}'},
            files={"file": ("tags.json", b'{"name":"tag_b"}', "application/json")},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "either pasted JSON or a file upload" in response.text

    def test_bulk_form_rejects_empty_payload(self, admin_client):
        response = admin_client.post(
            "/admin/tags/bulk",
            data={"json_text": "  "},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "Paste JSON in the text field" in response.text

    def test_bulk_form_rejects_invalid_json(self, admin_client):
        response = admin_client.post(
            "/admin/tags/bulk",
            data={"json_text": "{not valid json]"},
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "Invalid JSON" in response.text

    def test_bulk_form_accepts_file_upload_shorthand_single_object(
        self, admin_client, db_session
    ):
        payload = {"name": "file_uploaded_bulk_tag", "aliases": ["bulk_file_alias"]}
        response = admin_client.post(
            "/admin/tags/bulk",
            files={
                "file": (
                    "bulk.json",
                    json.dumps(payload).encode("utf-8"),
                    "application/json",
                )
            },
            follow_redirects=False,
        )
        assert response.status_code == 200

        created = db_session.scalar(
            select(Tag)
            .where(Tag.name == "file_uploaded_bulk_tag")
            .options(selectinload(Tag.aliases))
            .execution_options(include_pending=True)
        )
        assert created is not None
        assert {alias.alias for alias in created.aliases} == {"bulk_file_alias"}


@pytest.mark.integration
class TestAdminBulkTagUpsertPostConditions:
    def test_bulk_upsert_cycle_detection_returns_400(self, admin_client):
        payload = {
            "tags": [
                {
                    "name": "cycle_root",
                    "implications": [
                        {
                            "name": "cycle_mid",
                            "implications": [{"name": "cycle_root"}],
                        }
                    ],
                }
            ]
        }
        response = admin_client.post("/admin/tags/bulk-upsert", json=payload)
        assert response.status_code == 400
        assert "Cycle in tag implications" in response.text

    def test_bulk_upsert_add_only_aliases_and_implications(
        self, admin_client, db_session
    ):
        parent = TagFactory(name="bulk_existing_parent")
        child = TagFactory(name="bulk_existing_child")
        source = TagFactory(name="bulk_existing_source", aliases=["existing_alias"])
        source.implications.add(parent)  # ty:ignore[unresolved-attribute]
        db_session.flush()

        payload = {
            "tags": [
                {
                    "name": "bulk_existing_source",
                    "aliases": ["existing_alias", "new_alias"],
                    "implications": [
                        {"name": "bulk_existing_parent"},
                        {"name": "bulk_existing_child"},
                    ],
                }
            ]
        }
        response = admin_client.post("/admin/tags/bulk-upsert", json=payload)
        assert response.status_code == 200

        db_session.expire_all()
        refreshed = db_session.scalar(
            select(Tag)
            .where(Tag.name == "bulk_existing_source")
            .options(selectinload(Tag.aliases), selectinload(Tag.implications))
            .execution_options(include_pending=True)
        )
        assert refreshed is not None
        assert {alias.alias for alias in refreshed.aliases} == {
            "existing_alias",
            "new_alias",
        }
        assert {implication.name for implication in refreshed.implications} == {
            "bulk_existing_parent",
            "bulk_existing_child",
        }
