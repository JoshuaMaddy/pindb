"""Generated normalized names and HTMX duplicate-name check routes."""

from __future__ import annotations

from typing import TypeAlias, cast

import pytest

from pindb.database import Artist, Pin, PinSet, Shop, Tag
from tests.factories.artist import ArtistFactory
from tests.factories.pin import PinFactory
from tests.factories.pin_set import PersonalPinSetFactory, PinSetFactory
from tests.factories.shop import ShopFactory
from tests.factories.tag import TagFactory
from tests.fixtures.users import SUBJECT_USER_PARAMS

NormalizedEntity: TypeAlias = Artist | Pin | PinSet | Shop | Tag


def _assert_normalized_name(
    *,
    db_session,
    entity: NormalizedEntity,
    expected_name: str,
) -> None:
    db_session.refresh(entity)
    assert entity.normalized_name == expected_name


@pytest.mark.integration
class TestGeneratedNormalizedName:
    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_all_supported_entities_generate_normalized_name(
        self, db_session, admin_user, subject_user
    ):
        entities = [
            cast(
                NormalizedEntity,
                ArtistFactory(
                    name="Fancy Artist", approved=True, created_by=admin_user
                ),
            ),
            cast(
                NormalizedEntity,
                PinFactory(name="Fancy Pin", approved=True, created_by=admin_user),
            ),
            cast(
                NormalizedEntity,
                PinSetFactory(name="Fancy Set", approved=True, created_by=admin_user),
            ),
            cast(
                NormalizedEntity,
                PersonalPinSetFactory(
                    name="Fancy Personal Set",
                    owner_id=subject_user.id,
                    approved=True,
                    created_by=subject_user,
                ),
            ),
            cast(
                NormalizedEntity,
                ShopFactory(name="Fancy Shop", approved=True, created_by=admin_user),
            ),
            cast(
                NormalizedEntity,
                TagFactory(name="Fancy Tag", approved=True, created_by=admin_user),
            ),
        ]
        expected_names = [
            "fancy_artist",
            "fancy_pin",
            "fancy_set",
            "fancy_personal_set",
            "fancy_shop",
            "fancy_tag",
        ]

        for entity, expected_name in zip(entities, expected_names, strict=True):
            _assert_normalized_name(
                db_session=db_session,
                entity=entity,
                expected_name=expected_name,
            )

    def test_generated_normalized_name_updates_with_name_change(
        self, db_session, admin_user
    ):
        shop = cast(
            Shop,
            ShopFactory(name="Before Name", approved=True, created_by=admin_user),
        )
        db_session.refresh(shop)
        assert shop.normalized_name == "before_name"

        shop.name = "After Name"
        db_session.flush()
        db_session.refresh(shop)

        assert shop.normalized_name == "after_name"


@pytest.mark.integration
class TestCreateNameCheck:
    def test_returns_duplicate_fragment_for_each_editor_entity_kind(
        self, admin_client, admin_user
    ):
        ArtistFactory(name="Existing Artist", approved=True, created_by=admin_user)
        PinFactory(name="Existing Pin", approved=True, created_by=admin_user)
        PinSetFactory(name="Existing Set", approved=True, created_by=admin_user)
        ShopFactory(name="Existing Shop", approved=True, created_by=admin_user)
        TagFactory(name="Existing Tag", approved=True, created_by=admin_user)

        cases = [
            ("artist", "Existing Artist"),
            ("pin", "Existing Pin"),
            ("pin_set", "Existing Set"),
            ("shop", "Existing Shop"),
            ("tag", "Existing Tag"),
        ]
        for kind, name in cases:
            response = admin_client.get(
                "/create/check-name",
                params={"kind": kind, "name": name.lower()},
            )

            assert response.status_code == 200
            assert f"{name.lower()} already exists!" in response.text
            assert "text-error-main" in response.text

    def test_returns_empty_fragment_for_available_name(self, admin_client):
        response = admin_client.get(
            "/create/check-name",
            params={"kind": "shop", "name": "Unused Shop"},
        )

        assert response.status_code == 200
        assert response.text == ""

    def test_exclude_id_ignores_current_row(self, admin_client, admin_user):
        shop = cast(
            Shop,
            ShopFactory(name="Existing Shop", approved=True, created_by=admin_user),
        )

        response = admin_client.get(
            "/create/check-name",
            params={
                "kind": "shop",
                "name": "existing shop",
                "exclude_id": shop.id,
            },
        )

        assert response.status_code == 200
        assert response.text == ""

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_global_pin_set_scope_ignores_personal_sets(
        self, admin_client, admin_user, subject_user
    ):
        PersonalPinSetFactory(
            name="Shared Set",
            owner_id=subject_user.id,
            approved=True,
            created_by=subject_user,
        )

        response = admin_client.get(
            "/create/check-name",
            params={"kind": "pin_set", "name": "Shared Set"},
        )

        assert response.status_code == 200
        assert response.text == ""


@pytest.mark.integration
class TestPersonalSetNameCheck:
    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_personal_scope_checks_only_current_user(
        self,
        auth_client_as_subject,
        db_session,
        subject_user,
        other_editor_user,
        admin_user,
    ):
        PinSetFactory(name="Current Name", approved=True, created_by=admin_user)
        PersonalPinSetFactory(
            name="Current Name",
            owner_id=other_editor_user.id,
            approved=True,
            created_by=other_editor_user,
        )

        response = auth_client_as_subject.get(
            "/user/me/sets/check-name",
            params={"name": "Current Name"},
        )
        assert response.status_code == 200
        assert response.text == ""

        PersonalPinSetFactory(
            name="Current Name",
            owner_id=subject_user.id,
            approved=True,
            created_by=subject_user,
        )
        db_session.expire_all()

        response = auth_client_as_subject.get(
            "/user/me/sets/check-name",
            params={"name": "current name"},
        )

        assert response.status_code == 200
        assert "current name already exists!" in response.text

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_exclude_id_ignores_current_personal_set(
        self, auth_client_as_subject, subject_user
    ):
        pin_set = cast(
            PinSet,
            PersonalPinSetFactory(
                name="Personal Set",
                owner_id=subject_user.id,
                approved=True,
                created_by=subject_user,
            ),
        )

        response = auth_client_as_subject.get(
            "/user/me/sets/check-name",
            params={"name": "personal set", "exclude_id": pin_set.id},
        )

        assert response.status_code == 200
        assert response.text == ""
