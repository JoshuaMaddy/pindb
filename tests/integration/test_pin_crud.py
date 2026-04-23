"""Integration tests for pin GET routes and auth enforcement on create/edit/delete.

Role model under test:
- `/create/*` requires the `editor` dependency (editor OR admin).
- `/delete/*` requires admin. It's POST, not GET, and returns a 303 redirect.
- `/edit/*` requires editor (ownership enforced by `assert_editor_can_edit`).
"""

import pytest

from tests.factories.pin import PinFactory
from tests.factories.shop import ShopFactory


@pytest.mark.integration
class TestGetPin:
    def test_nonexistent_pin_redirects(self, client):
        response = client.get("/get/pin/999999", follow_redirects=False)
        assert response.status_code in (302, 307)

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
    """`/create/pin` requires the `editor` role. Regular users get 403."""

    def test_unauthenticated_get_returns_401(self, client):
        response = client.get("/create/pin")
        assert response.status_code == 401

    def test_regular_user_get_returns_403(self, auth_client):
        """`test_user` is a plain authenticated user — not editor or admin."""
        response = auth_client.get("/create/pin")
        assert response.status_code == 403

    def test_editor_get_returns_200(self, editor_client):
        response = editor_client.get("/create/pin")
        assert response.status_code == 200

    def test_admin_get_returns_200(self, admin_client):
        response = admin_client.get("/create/pin")
        assert response.status_code == 200

    def test_unauthenticated_post_returns_401(self, client):
        response = client.post("/create/pin", data={})
        assert response.status_code == 401

    def test_regular_user_post_returns_403(self, auth_client):
        response = auth_client.post("/create/pin", data={})
        assert response.status_code == 403

    def test_editor_post_builds_form_validator(self, editor_client):
        """Guards against ForwardRef regressions on enum Form params.

        `from __future__ import annotations` in `_pin_shared.py` turns enum
        annotations into ForwardRefs that FastAPI cannot resolve, raising
        `PydanticUserError` at request time. Posting any valid-enum value as
        editor builds and exercises the Form validator; crashes surface as 5xx.
        """
        response = editor_client.post(
            "/create/pin",
            data={
                "name": "FormValidatorProbe",
                "acquisition_type": "single",
                "grade_names": "standard",
                "grade_prices": "",
                "currency_id": "999",
                "posts": "1",
            },
        )
        assert response.status_code < 500, response.text[:500]


@pytest.mark.integration
class TestDuplicatePin:
    """`/create/pin?duplicate_from=<id>` prefills the form from an existing pin."""

    def test_duplicate_from_unknown_pin_returns_404(self, editor_client):
        response = editor_client.get("/create/pin?duplicate_from=999999")
        assert response.status_code == 404

    def test_duplicate_prefills_name_and_shop(self, editor_client, db_session):
        shop = ShopFactory(name="Duplicator Shop")
        source = PinFactory(name="Source Pin To Duplicate", shops={shop})
        response = editor_client.get(
            f"/create/pin?duplicate_from={source.id}"  # ty:ignore[unresolved-attribute]
        )
        assert response.status_code == 200
        body = response.text
        assert "Create a Pin" in body
        assert "Duplicating" in body
        assert "Source Pin To Duplicate" in body
        assert "Duplicator Shop" in body

    def test_duplicate_requires_editor(self, auth_client, db_session):
        source = PinFactory()
        response = auth_client.get(
            f"/create/pin?duplicate_from={source.id}"  # ty:ignore[unresolved-attribute]
        )
        assert response.status_code == 403

    def test_pin_page_shows_duplicate_link_to_editor(self, editor_client, db_session):
        pin = PinFactory(name="Has Duplicate Button")
        response = editor_client.get(
            f"/get/pin/{pin.id}"  # ty:ignore[unresolved-attribute]
        )
        assert response.status_code == 200
        assert (
            f"/create/pin?duplicate_from={pin.id}"  # ty:ignore[unresolved-attribute]
            in response.text
        )

    def test_pin_page_hides_duplicate_link_from_regular_user(
        self, auth_client, db_session
    ):
        pin = PinFactory(name="No Duplicate Button")
        response = auth_client.get(
            f"/get/pin/{pin.id}"  # ty:ignore[unresolved-attribute]
        )
        assert response.status_code == 200
        assert "duplicate_from" not in response.text


@pytest.mark.integration
class TestDeletePinAuthEnforcement:
    """`POST /delete/pin/{id}` is admin-only and returns a 303 redirect on success."""

    def test_unauthenticated_delete_returns_401(self, client, db_session):
        pin = PinFactory()
        response = client.post(
            f"/delete/pin/{pin.id}",  # ty:ignore[unresolved-attribute]
            follow_redirects=False,
        )
        assert response.status_code == 401

    def test_regular_user_delete_returns_403(self, auth_client, db_session):
        pin = PinFactory()
        response = auth_client.post(
            f"/delete/pin/{pin.id}",  # ty:ignore[unresolved-attribute]
            follow_redirects=False,
        )
        assert response.status_code == 403

    def test_editor_delete_returns_403(self, editor_client, db_session):
        """Editors cannot hard/soft delete — admin only."""
        pin = PinFactory()
        response = editor_client.post(
            f"/delete/pin/{pin.id}",  # ty:ignore[unresolved-attribute]
            follow_redirects=False,
        )
        assert response.status_code == 403

    def test_admin_delete_soft_deletes(self, admin_client, db_session):
        from sqlalchemy import select

        from pindb.database import Pin

        pin = PinFactory()
        pin_id = pin.id  # ty:ignore[unresolved-attribute]
        response = admin_client.post(f"/delete/pin/{pin_id}", follow_redirects=False)
        assert response.status_code == 303

        # Route committed its savepoint; our session hasn't seen that yet.
        db_session.expire_all()

        # Soft delete: row still exists, hidden from default queries
        visible = db_session.scalar(select(Pin).where(Pin.id == pin_id))
        assert visible is None

        from typing import Any

        opts: Any = {"include_deleted": True, "include_pending": True}
        raw = db_session.scalar(
            select(Pin).where(Pin.id == pin_id).execution_options(**opts)
        )
        assert raw is not None
        assert raw.deleted_at is not None
