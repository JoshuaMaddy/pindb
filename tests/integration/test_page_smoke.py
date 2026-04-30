"""Smoke tests for public list and entity detail pages."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, cast

import pytest

from pindb.database.artist import Artist
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.database.tag import Tag
from tests.factories.artist import ArtistFactory
from tests.factories.pin import PinFactory
from tests.factories.pin_set import PinSetFactory
from tests.factories.shop import ShopFactory
from tests.factories.tag import TagFactory


class SmokeEntity(Protocol):
    id: int


@pytest.mark.integration
class TestPublicPageSmoke:
    @pytest.mark.parametrize(
        "path",
        [
            "/list/",
            "/list/shops",
            "/list/artists",
            "/list/tags",
            "/list/pin_sets",
        ],
    )
    def test_list_pages_return_200(self, anon_client, admin_user, path: str):
        ShopFactory(name="Smoke Shop", approved=True, created_by=admin_user)
        ArtistFactory(name="Smoke Artist", approved=True, created_by=admin_user)
        TagFactory(name="smoke_tag", approved=True, created_by=admin_user)
        PinSetFactory(name="Smoke Set", approved=True, created_by=admin_user)

        response = anon_client.get(path)

        assert response.status_code == 200

    def test_user_profile_page_returns_200(self, anon_client, test_user):
        response = anon_client.get(f"/user/{test_user.username}")

        assert response.status_code == 200
        assert test_user.username in response.text

    @pytest.mark.parametrize(
        ("entity_key", "path_for_entity", "expected_text"),
        [
            ("pin", lambda entity: f"/get/pin/{entity.id}", "Smoke Pin"),
            ("shop", lambda entity: f"/get/shop/{entity.id}", "Smoke Shop"),
            ("artist", lambda entity: f"/get/artist/{entity.id}", "Smoke Artist"),
            ("tag", lambda entity: f"/get/tag/{entity.id}", "Smoke Tag"),
            ("pin_set", lambda entity: f"/get/pin_set/{entity.id}", "Smoke Set"),
        ],
    )
    def test_get_pages_return_200(
        self,
        anon_client,
        admin_user,
        entity_key: str,
        path_for_entity: Callable[[SmokeEntity], str],
        expected_text: str,
    ):
        entities: dict[str, SmokeEntity] = {
            "pin": cast(
                Pin,
                PinFactory(
                    name="Smoke Pin",
                    approved=True,
                    created_by=admin_user,
                ),
            ),
            "shop": cast(
                Shop,
                ShopFactory(
                    name="Smoke Shop",
                    approved=True,
                    created_by=admin_user,
                ),
            ),
            "artist": cast(
                Artist,
                ArtistFactory(
                    name="Smoke Artist",
                    approved=True,
                    created_by=admin_user,
                ),
            ),
            "tag": cast(
                Tag,
                TagFactory(
                    name="smoke_tag",
                    approved=True,
                    created_by=admin_user,
                ),
            ),
            "pin_set": cast(
                PinSet,
                PinSetFactory(
                    name="Smoke Set",
                    approved=True,
                    created_by=admin_user,
                ),
            ),
        }
        entity = entities[entity_key]

        response = anon_client.get(path_for_entity(entity))

        assert response.status_code == 200
        assert expected_text in response.text
