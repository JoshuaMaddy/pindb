"""Integration tests for /list/* routes — simple read-only pages."""

import pytest

from tests.factories.artist import ArtistFactory
from tests.factories.pin_set import PinSetFactory
from tests.factories.shop import ShopFactory


@pytest.mark.integration
class TestListShops:
    def test_empty_list_returns_200(self, auth_client):
        response = auth_client.get("/list/shops")
        assert response.status_code == 200

    def test_shows_shop_name(self, auth_client, db_session):
        ShopFactory(name="Acme Pins")
        response = auth_client.get("/list/shops")
        assert response.status_code == 200
        assert "Acme Pins" in response.text

    def test_shows_multiple_shops(self, auth_client, db_session):
        ShopFactory(name="Shop Alpha")
        ShopFactory(name="Shop Beta")
        response = auth_client.get("/list/shops")
        assert "Shop Alpha" in response.text
        assert "Shop Beta" in response.text


@pytest.mark.integration
class TestListArtists:
    def test_empty_list_returns_200(self, auth_client):
        response = auth_client.get("/list/artists")
        assert response.status_code == 200

    def test_shows_artist_name(self, auth_client, db_session):
        ArtistFactory(name="Famous Artist")
        response = auth_client.get("/list/artists")
        assert "Famous Artist" in response.text


@pytest.mark.integration
class TestListPinSets:
    def test_empty_list_returns_200(self, auth_client):
        response = auth_client.get("/list/pin_sets")
        assert response.status_code == 200

    def test_shows_pin_set_name(self, auth_client, db_session):
        PinSetFactory(name="My Awesome Set")
        response = auth_client.get("/list/pin_sets")
        assert "My Awesome Set" in response.text


@pytest.mark.integration
class TestListDetailedView:
    """The shared entity_list_items factory must render both grid and detailed."""

    def test_shops_detailed(self, auth_client, db_session):
        ShopFactory(name="Detailed Shop")
        response = auth_client.get("/list/shops?view=detailed")
        assert response.status_code == 200
        assert "Detailed Shop" in response.text

    def test_artists_detailed(self, auth_client, db_session):
        ArtistFactory(name="Detailed Artist")
        response = auth_client.get("/list/artists?view=detailed")
        assert response.status_code == 200
        assert "Detailed Artist" in response.text

    def test_pin_sets_detailed(self, auth_client, db_session):
        PinSetFactory(name="Detailed Set")
        response = auth_client.get("/list/pin_sets?view=detailed")
        assert response.status_code == 200
        assert "Detailed Set" in response.text
