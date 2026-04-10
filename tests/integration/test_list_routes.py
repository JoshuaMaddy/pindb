"""Integration tests for /list/* routes — simple read-only pages."""

import pytest

from tests.factories.artist import ArtistFactory
from tests.factories.pin_set import PinSetFactory
from tests.factories.shop import ShopFactory


@pytest.mark.integration
class TestListShops:
    def test_empty_list_returns_200(self, client):
        response = client.get("/list/shops")
        assert response.status_code == 200

    def test_shows_shop_name(self, client, db_session):
        ShopFactory(name="Acme Pins")
        response = client.get("/list/shops")
        assert response.status_code == 200
        assert "Acme Pins" in response.text

    def test_shows_multiple_shops(self, client, db_session):
        ShopFactory(name="Shop Alpha")
        ShopFactory(name="Shop Beta")
        response = client.get("/list/shops")
        assert "Shop Alpha" in response.text
        assert "Shop Beta" in response.text


@pytest.mark.integration
class TestListArtists:
    def test_empty_list_returns_200(self, client):
        response = client.get("/list/artists")
        assert response.status_code == 200

    def test_shows_artist_name(self, client, db_session):
        ArtistFactory(name="Famous Artist")
        response = client.get("/list/artists")
        assert "Famous Artist" in response.text


@pytest.mark.integration
class TestListPinSets:
    def test_empty_list_returns_200(self, client):
        response = client.get("/list/pin_sets")
        assert response.status_code == 200

    def test_shows_pin_set_name(self, client, db_session):
        PinSetFactory(name="My Awesome Set")
        response = client.get("/list/pin_sets")
        assert "My Awesome Set" in response.text
