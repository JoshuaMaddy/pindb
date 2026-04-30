"""Cross-cutting route smoke: legal, health, OG, tag helpers, OAuth stubs."""

from __future__ import annotations

import importlib

import pytest

from tests.factories.tag import TagFactory

auth_router_module = importlib.import_module("pindb.routes.auth.router")


@pytest.mark.integration
class TestLegalPages:
    @pytest.mark.parametrize("path", ["/about", "/privacy", "/terms"])
    def test_legal_pages_return_200(self, anon_client, path: str):
        response = anon_client.get(path)
        assert response.status_code == 200
        assert "<html" in response.text.lower()


@pytest.mark.integration
class TestHealthRoute:
    def test_healthz_returns_ok(self, anon_client):
        response = anon_client.get("/healthz")
        assert response.status_code == 200
        assert response.text == "ok"


@pytest.mark.integration
class TestUserSetCreatePage:
    def test_create_set_page_requires_auth(self, anon_client):
        response = anon_client.get("/user/me/sets/new")
        assert response.status_code == 401

    def test_create_set_page_renders_for_authenticated_user(self, auth_client):
        response = auth_client.get("/user/me/sets/new")
        assert response.status_code == 200
        assert "Create" in response.text


@pytest.mark.integration
class TestOgImageRoutes:
    def test_tag_og_image_returns_webp(self, anon_client, admin_user):
        tag = TagFactory(name="og_image_tag", approved=True, created_by=admin_user)
        response = anon_client.get(
            f"/get/og-image/tag/{tag.id}"  # ty:ignore[unresolved-attribute]
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/webp")
        assert response.headers.get("cache-control") == "public, max-age=3600"
        assert response.content

    def test_og_image_rejects_unknown_entity_type(self, anon_client):
        response = anon_client.get("/get/og-image/not_real/1")
        assert response.status_code == 404


@pytest.mark.integration
class TestTagHelperRoutes:
    async def _fake_tag_options(self, _index_name: str, _q: str):
        return [{"value": "1", "label": "Tag One"}, {"value": "2", "label": "Tag Two"}]

    def test_tag_options_returns_json_and_supports_exclude(
        self, anon_client, monkeypatch
    ):
        monkeypatch.setattr(
            "pindb.routes.get.tag.search_entity_options",
            self._fake_tag_options,
        )
        response = anon_client.get(
            "/get/tag-options", params={"q": "tag", "exclude_id": 2}
        )
        assert response.status_code == 200
        assert response.json() == [{"value": "1", "label": "Tag One"}]

    def test_tag_implication_preview_empty_when_no_tags(self, anon_client):
        response = anon_client.get("/get/tag-implication-preview")
        assert response.status_code == 200
        assert response.text == ""

    def test_tag_implication_preview_renders_for_selected_tags(
        self, anon_client, db_session, admin_user
    ):
        implied = TagFactory(name="implied_tag", approved=True, created_by=admin_user)
        selected = TagFactory(name="selected_tag", approved=True, created_by=admin_user)
        selected.implications.add(implied)  # ty:ignore[unresolved-attribute]
        db_session.flush()

        response = anon_client.get(
            "/get/tag-implication-preview",
            params={"tag_ids": [selected.id]},  # ty:ignore[unresolved-attribute]
        )
        assert response.status_code == 200
        assert response.text != ""


@pytest.mark.integration
class TestAdditionalOauthRoutes:
    def test_meta_login_returns_404_when_provider_disabled(
        self, anon_client, monkeypatch
    ):
        monkeypatch.setattr(
            auth_router_module, "provider_enabled", lambda _provider: False
        )
        response = anon_client.get("/auth/meta", follow_redirects=False)
        assert response.status_code == 404

    def test_meta_callback_returns_404_when_provider_disabled(
        self, anon_client, monkeypatch
    ):
        monkeypatch.setattr(
            auth_router_module, "provider_enabled", lambda _provider: False
        )
        response = anon_client.get("/auth/meta/callback", follow_redirects=False)
        assert response.status_code == 404

    def test_discord_callback_returns_404_when_provider_disabled(
        self, anon_client, monkeypatch
    ):
        monkeypatch.setattr(
            auth_router_module, "provider_enabled", lambda _provider: False
        )
        response = anon_client.get("/auth/discord/callback", follow_redirects=False)
        assert response.status_code == 404
