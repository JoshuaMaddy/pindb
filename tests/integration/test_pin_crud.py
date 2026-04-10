"""Integration tests for pin GET routes and auth enforcement on create/edit/delete."""

import pytest

from tests.factories.pin import PinFactory
from tests.factories.shop import ShopFactory


@pytest.mark.integration
class TestGetPin:
    def test_nonexistent_pin_redirects(self, client):
        response = client.get("/get/pin/999999", follow_redirects=False)
        assert response.status_code in (302, 307)  # RedirectResponse defaults to 307

    def test_existing_pin_returns_200(self, client, db_session):
        pin = PinFactory(name="Special Pikachu Pin")
        response = client.get(f"/get/pin/{pin.id}")  # ty:ignore[unresolved-attribute]
        assert response.status_code == 200
        assert "Special Pikachu Pin" in response.text

    def test_existing_pin_shows_shops(self, client, db_session):
        shop = ShopFactory(name="Pokemon Store")
        pin = PinFactory(shops={shop})
        response = client.get(f"/get/pin/{pin.id}")  # ty:ignore[unresolved-attribute]
        assert response.status_code == 200
        assert "Pokemon Store" in response.text


@pytest.mark.integration
class TestCreatePinAuthEnforcement:
    def test_unauthenticated_get_returns_401(self, client):
        response = client.get("/create/pin")
        assert response.status_code == 401

    def test_non_admin_get_returns_403(self, auth_client):
        response = auth_client.get("/create/pin")
        assert response.status_code == 403

    def test_admin_get_returns_200(self, admin_client):
        response = admin_client.get("/create/pin")
        assert response.status_code == 200

    def test_unauthenticated_post_returns_401(self, client):
        response = client.post("/create/pin", data={})
        assert response.status_code == 401

    def test_non_admin_post_returns_403(self, auth_client):
        response = auth_client.post("/create/pin", data={})
        assert response.status_code == 403


@pytest.mark.integration
class TestDeletePinAuthEnforcement:
    # Delete uses GET /delete/pin/{id} (not POST)
    def test_unauthenticated_delete_returns_401(self, client, db_session):
        pin = PinFactory()
        response = client.get(f"/delete/pin/{pin.id}")  # ty:ignore[unresolved-attribute]
        assert response.status_code == 401

    def test_non_admin_delete_returns_403(self, auth_client, db_session):
        pin = PinFactory()
        response = auth_client.get(f"/delete/pin/{pin.id}")  # ty:ignore[unresolved-attribute]
        assert response.status_code == 403

    def test_admin_delete_succeeds(self, admin_client, db_session):
        pin = PinFactory()
        pin_id = pin.id  # ty:ignore[unresolved-attribute]
        response = admin_client.get(f"/delete/pin/{pin_id}")
        assert response.status_code == 200
