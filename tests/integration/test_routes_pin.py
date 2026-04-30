"""Integration tests for pin GET/create/edit/delete routes and auth enforcement.

Role model under test:
- ``/create/*`` requires the ``editor`` dependency (editor OR admin).
- ``/delete/*`` requires admin. It's POST, not GET, and returns a 303 redirect.
- ``/edit/*`` requires editor (ownership enforced by ``assert_editor_can_edit``).
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pindb.database import Pin, UserOwnedPin, UserWantedPin
from pindb.database.artist import Artist
from pindb.database.joins import user_favorite_pins
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.database.tag import Tag
from tests.factories.artist import ArtistFactory
from tests.factories.pin import PinFactory
from tests.factories.pin_set import PersonalPinSetFactory
from tests.factories.shop import ShopFactory
from tests.factories.tag import TagFactory
from tests.integration.helpers.pin_payloads import pin_form_data


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

    def test_id_only_url_redirects_to_slugged_form(self, client, db_session):
        pin = PinFactory(name="Special Pikachu Pin")
        response = client.get(
            f"/get/pin/{pin.id}",  # ty:ignore[unresolved-attribute]
            follow_redirects=False,
        )
        assert response.status_code == 301
        assert response.headers["location"].endswith(
            f"/get/pin/special_pikachu_pin/{pin.id}"  # ty:ignore[unresolved-attribute]
        )

    def test_wrong_slug_redirects_to_canonical(self, client, db_session):
        pin = PinFactory(name="Special Pikachu Pin")
        response = client.get(
            f"/get/pin/wrong_slug/{pin.id}",  # ty:ignore[unresolved-attribute]
            follow_redirects=False,
        )
        assert response.status_code == 301
        assert response.headers["location"].endswith(
            f"/get/pin/special_pikachu_pin/{pin.id}"  # ty:ignore[unresolved-attribute]
        )

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

    def test_duplicate_prefills_tags_without_server_error(
        self, editor_client, db_session, admin_user
    ):
        tag = TagFactory(name="dup_tag_prefill", approved=True, created_by=admin_user)
        source = PinFactory(name="Source With Tags")
        source.explicit_tags.add(tag)  # ty:ignore[unresolved-attribute]
        db_session.flush()

        response = editor_client.get(
            f"/create/pin?duplicate_from={source.id}"  # ty:ignore[unresolved-attribute]
        )
        assert response.status_code == 200
        body = response.text
        assert "Source With Tags" in body
        assert f'value="{tag.id}"' in body  # ty:ignore[unresolved-attribute]

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
        pin = PinFactory()
        pin_id = pin.id  # ty:ignore[unresolved-attribute]
        response = admin_client.post(f"/delete/pin/{pin_id}", follow_redirects=False)
        assert response.status_code == 303

        db_session.expire_all()

        visible = db_session.scalar(select(Pin).where(Pin.id == pin_id))
        assert visible is None

        opts: Any = {"include_deleted": True, "include_pending": True}
        raw = db_session.scalar(
            select(Pin).where(Pin.id == pin_id).execution_options(**opts)
        )
        assert raw is not None
        assert raw.deleted_at is not None


@pytest.mark.integration
class TestPinWriteRoutes:
    def test_create_pin_post_persists_relations(
        self, admin_client, db_session, png_upload
    ):
        shop = cast(Shop, ShopFactory())
        tag = cast(Tag, TagFactory())
        artist = cast(Artist, ArtistFactory())
        pin_set = cast(PinSet, PersonalPinSetFactory(owner_id=None))
        variant = cast(Pin, PinFactory())
        copy_pin = cast(Pin, PinFactory())

        response = admin_client.post(
            "/create/pin",
            data=pin_form_data(
                name="Created Through Route",
                shop_ids=[shop.id],
                tag_ids=[tag.id],
                artist_ids=[artist.id],
                pin_sets_ids=[pin_set.id],
                variant_pin_ids=[variant.id],
                unauthorized_copy_pin_ids=[copy_pin.id],
            ),
            files={"front_image": png_upload},
            follow_redirects=False,
        )
        assert response.status_code == 200
        assert "HX-Redirect" in response.headers

        created = db_session.scalar(
            select(Pin)
            .where(Pin.name == "Created Through Route")
            .options(
                selectinload(Pin.shops),
                selectinload(Pin.explicit_tags),
                selectinload(Pin.artists),
                selectinload(Pin.sets),
                selectinload(Pin.links),
                selectinload(Pin.variants),
                selectinload(Pin.unauthorized_copies),
            )
            .execution_options(include_pending=True)
        )
        assert created is not None
        assert any(loaded_shop.id == shop.id for loaded_shop in created.shops)
        assert any(loaded_tag.id == tag.id for loaded_tag in created.explicit_tags)
        assert any(loaded_artist.id == artist.id for loaded_artist in created.artists)
        assert any(loaded_set.id == pin_set.id for loaded_set in created.sets)
        assert any(loaded_pin.id == variant.id for loaded_pin in created.variants)
        assert any(
            loaded_pin.id == copy_pin.id for loaded_pin in created.unauthorized_copies
        )
        assert len(created.links) == 2

    def test_edit_pin_post_updates_fields_and_skips_self_variant(
        self, admin_client, db_session, admin_user
    ):
        source_pin = cast(
            Pin,
            PinFactory(name="Before Edit", approved=True, created_by=admin_user),
        )
        new_shop = cast(Shop, ShopFactory())
        new_tag = cast(Tag, TagFactory())
        new_artist = cast(Artist, ArtistFactory())
        new_set = cast(PinSet, PersonalPinSetFactory(owner_id=None))
        related_pin = cast(Pin, PinFactory())
        source_pin_id = source_pin.id

        response = admin_client.post(
            f"/edit/pin/{source_pin_id}",
            data=pin_form_data(
                name="After Edit",
                shop_ids=[new_shop.id],
                tag_ids=[new_tag.id],
                artist_ids=[new_artist.id],
                pin_sets_ids=[new_set.id],
                variant_pin_ids=[source_pin_id, related_pin.id],
            ),
            follow_redirects=False,
        )
        assert response.status_code == 200
        assert "HX-Redirect" in response.headers

        db_session.expire_all()
        refreshed = db_session.scalar(
            select(Pin)
            .where(Pin.id == source_pin_id)
            .options(
                selectinload(Pin.shops),
                selectinload(Pin.explicit_tags),
                selectinload(Pin.artists),
                selectinload(Pin.sets),
                selectinload(Pin.variants),
            )
            .execution_options(include_pending=True)
        )
        assert refreshed is not None
        assert refreshed.name == "After Edit"
        assert any(loaded_shop.id == new_shop.id for loaded_shop in refreshed.shops)
        assert any(
            loaded_tag.id == new_tag.id for loaded_tag in refreshed.explicit_tags
        )
        assert any(
            loaded_artist.id == new_artist.id for loaded_artist in refreshed.artists
        )
        assert any(loaded_set.id == new_set.id for loaded_set in refreshed.sets)
        assert all(loaded_pin.id != source_pin_id for loaded_pin in refreshed.variants)
        assert any(loaded_pin.id == related_pin.id for loaded_pin in refreshed.variants)


@pytest.mark.integration
class TestGetPinForAuthenticatedUser:
    def test_get_pin_loads_user_collection_context(
        self, auth_client, db_session, test_user, admin_user
    ):
        pin = cast(
            Pin,
            PinFactory(name="User Context Pin", approved=True, created_by=admin_user),
        )
        pin_id = pin.id
        personal_set = cast(PinSet, PersonalPinSetFactory(owner_id=test_user.id))
        db_session.execute(
            user_favorite_pins.insert().values(user_id=test_user.id, pin_id=pin_id)
        )
        db_session.add(
            UserOwnedPin(
                user_id=test_user.id,
                pin_id=pin_id,
                grade_id=None,
                quantity=2,
                tradeable_quantity=1,
            )
        )
        db_session.add(
            UserWantedPin(user_id=test_user.id, pin_id=pin_id, grade_id=None)
        )
        db_session.flush()

        response = auth_client.get(f"/get/pin/{pin_id}")
        assert response.status_code == 200
        assert "User Context Pin" in response.text
        assert str(personal_set.name) in response.text
