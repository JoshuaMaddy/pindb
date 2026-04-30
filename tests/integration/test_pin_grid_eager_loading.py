"""Regression tests for pin preview grids rendered from async route sessions."""

from __future__ import annotations

from typing import cast

import pytest

from pindb.database.artist import Artist
from pindb.database.joins import (
    pin_set_memberships,
    pins_tags,
    user_favorite_pins,
)
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.database.tag import Tag
from tests.factories.artist import ArtistFactory
from tests.factories.pin import PinFactory
from tests.factories.pin_set import PinSetFactory
from tests.factories.shop import ShopFactory
from tests.factories.tag import TagFactory
from tests.fixtures.users import SUBJECT_USER_PARAMS


@pytest.mark.integration
class TestPinGridEagerLoading:
    def test_tag_page_renders_pin_grid_with_shop_and_artist(
        self,
        anon_client,
        db_session,
        admin_user,
    ):
        shop = cast(
            Shop, ShopFactory(name="Grid Shop", approved=True, created_by=admin_user)
        )
        artist = cast(
            Artist,
            ArtistFactory(name="Grid Artist", approved=True, created_by=admin_user),
        )
        tag = cast(
            Tag, TagFactory(name="grid_tag", approved=True, created_by=admin_user)
        )
        pin = cast(
            Pin,
            PinFactory(
                name="Grid Pin",
                shops={shop},
                artists={artist},
                approved=True,
                created_by=admin_user,
            ),
        )
        db_session.execute(pins_tags.insert().values(pin_id=pin.id, tag_id=tag.id))
        db_session.flush()

        response = anon_client.get(f"/get/tag/{tag.id}")

        assert response.status_code == 200
        assert "Grid Pin" in response.text
        assert "Grid Shop" in response.text
        assert "Grid Artist" in response.text

    def test_artist_page_renders_pin_grid_with_shop(
        self,
        anon_client,
        admin_user,
    ):
        shop = cast(
            Shop,
            ShopFactory(name="Artist Grid Shop", approved=True, created_by=admin_user),
        )
        artist = cast(
            Artist,
            ArtistFactory(
                name="Artist Grid Artist",
                approved=True,
                created_by=admin_user,
            ),
        )
        pin = cast(
            Pin,
            PinFactory(
                name="Artist Grid Pin",
                shops={shop},
                artists={artist},
                approved=True,
                created_by=admin_user,
            ),
        )

        response = anon_client.get(f"/get/artist/{artist.id}")

        assert response.status_code == 200
        assert "Artist Grid Pin" in response.text
        assert "Artist Grid Shop" in response.text
        assert "Artist Grid Artist" in response.text

    def test_shop_page_renders_pin_grid_with_artist(
        self,
        anon_client,
        admin_user,
    ):
        shop = cast(
            Shop,
            ShopFactory(name="Shop Grid Shop", approved=True, created_by=admin_user),
        )
        artist = cast(
            Artist,
            ArtistFactory(
                name="Shop Grid Artist", approved=True, created_by=admin_user
            ),
        )
        pin = cast(
            Pin,
            PinFactory(
                name="Shop Grid Pin",
                shops={shop},
                artists={artist},
                approved=True,
                created_by=admin_user,
            ),
        )

        response = anon_client.get(f"/get/shop/{shop.id}")

        assert response.status_code == 200
        assert "Shop Grid Pin" in response.text
        assert "Shop Grid Shop" in response.text
        assert "Shop Grid Artist" in response.text

    def test_pin_set_page_renders_pin_grid_with_shop_and_artist(
        self,
        anon_client,
        db_session,
        admin_user,
    ):
        shop = cast(
            Shop,
            ShopFactory(name="Set Grid Shop", approved=True, created_by=admin_user),
        )
        artist = cast(
            Artist,
            ArtistFactory(name="Set Grid Artist", approved=True, created_by=admin_user),
        )
        pin_set = cast(
            PinSet,
            PinSetFactory(name="Grid Set", approved=True, created_by=admin_user),
        )
        pin = cast(
            Pin,
            PinFactory(
                name="Set Grid Pin",
                shops={shop},
                artists={artist},
                approved=True,
                created_by=admin_user,
            ),
        )
        db_session.execute(
            pin_set_memberships.insert().values(
                pin_id=pin.id,
                set_id=pin_set.id,
                position=0,
            )
        )
        db_session.flush()

        response = anon_client.get(f"/get/pin_set/{pin_set.id}")

        assert response.status_code == 200
        assert "Set Grid Pin" in response.text
        assert "Set Grid Shop" in response.text
        assert "Set Grid Artist" in response.text

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_user_profile_preview_renders_pin_grid_with_shop_and_artist(
        self,
        auth_client_as_subject,
        db_session,
        subject_user,
        admin_user,
    ):
        shop = cast(
            Shop,
            ShopFactory(name="Profile Grid Shop", approved=True, created_by=admin_user),
        )
        artist = cast(
            Artist,
            ArtistFactory(
                name="Profile Grid Artist",
                approved=True,
                created_by=admin_user,
            ),
        )
        pin = cast(
            Pin,
            PinFactory(
                name="Profile Grid Pin",
                shops={shop},
                artists={artist},
                approved=True,
                created_by=admin_user,
            ),
        )
        db_session.execute(
            user_favorite_pins.insert().values(
                user_id=subject_user.id,
                pin_id=pin.id,
            )
        )
        db_session.flush()

        response = auth_client_as_subject.get(f"/user/{subject_user.username}")

        assert response.status_code == 200
        assert "Profile Grid Pin" in response.text
        assert "Profile Grid Shop" in response.text
        assert "Profile Grid Artist" in response.text
