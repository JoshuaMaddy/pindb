"""Deeper integration coverage for user set routes and HTMX branches."""

from __future__ import annotations

import importlib
from typing import cast

import pytest
from sqlalchemy import select

from pindb.database import PinSet
from pindb.database.joins import pin_set_memberships
from pindb.database.pin import Pin
from tests.factories.pin import PinFactory
from tests.factories.pin_set import PersonalPinSetFactory
from tests.fixtures.users import SUBJECT_USER_PARAMS

user_sets_module = importlib.import_module("pindb.routes.user.sets")


@pytest.mark.integration
class TestUserSetEditAndNameChecks:
    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_personal_set_name_check_detects_conflict(
        self, auth_client_as_subject, subject_user
    ):
        existing = cast(
            PinSet,
            PersonalPinSetFactory(owner_id=subject_user.id, name="Conflict Name"),
        )
        response = auth_client_as_subject.get(
            "/user/me/sets/check-name",
            params={
                "name": "conflict name",
                "exclude_id": existing.id,
            },
        )
        assert response.status_code == 200

        response = auth_client_as_subject.get(
            "/user/me/sets/check-name",
            params={"name": "Conflict Name"},
        )
        assert response.status_code == 200
        assert "already exists" in response.text.lower()

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_set_edit_page_and_update_flow(
        self, auth_client_as_subject, db_session, subject_user
    ):
        pin_set = cast(
            PinSet,
            PersonalPinSetFactory(owner_id=subject_user.id, name="Before Set Name"),
        )
        response = auth_client_as_subject.get(f"/user/sets/{pin_set.id}/edit")
        assert response.status_code == 200
        assert "Before Set Name" in response.text

        update = auth_client_as_subject.post(
            f"/user/sets/{pin_set.id}/edit",
            data={"name": "After Set Name", "description": "updated"},
            follow_redirects=False,
        )
        assert update.status_code == 303

        db_session.expire_all()
        refreshed = db_session.get(PinSet, pin_set.id)
        assert refreshed is not None
        assert refreshed.name == "After Set Name"
        assert refreshed.description == "updated"


@pytest.mark.integration
class TestUserSetHtmxMembershipBranches:
    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_add_pin_hx_search_row_branch(
        self, auth_client_as_subject, db_session, subject_user, admin_user
    ):
        pin_set = cast(PinSet, PersonalPinSetFactory(owner_id=subject_user.id))
        pin = cast(Pin, PinFactory(approved=True, created_by=admin_user))
        response = auth_client_as_subject.post(
            f"/user/sets/{pin_set.id}/pins/{pin.id}",
            headers={"HX-Request": "true", "HX-Target": f"search-row-{pin.id}"},
        )
        assert response.status_code == 200
        assert "hx-swap-oob" in response.text

        exists = db_session.execute(
            select(pin_set_memberships).where(
                pin_set_memberships.c.set_id == pin_set.id,
                pin_set_memberships.c.pin_id == pin.id,
            )
        ).first()
        assert exists is not None

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_remove_pin_hx_pin_row_branch(
        self, auth_client_as_subject, db_session, subject_user, admin_user
    ):
        pin_set = cast(PinSet, PersonalPinSetFactory(owner_id=subject_user.id))
        pin = cast(Pin, PinFactory(approved=True, created_by=admin_user))
        db_session.execute(
            pin_set_memberships.insert().values(
                set_id=pin_set.id,
                pin_id=pin.id,
                position=0,
            )
        )
        db_session.flush()

        response = auth_client_as_subject.request(
            method="DELETE",
            url=f"/user/sets/{pin_set.id}/pins/{pin.id}",
            headers={"HX-Request": "true", "HX-Target": f"pin-row-{pin.id}"},
        )
        assert response.status_code == 200
        assert "hx-swap-oob" in response.text

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_search_pins_for_set_route_uses_search_results(
        self, auth_client_as_subject, monkeypatch, subject_user, admin_user
    ):
        pin_set = cast(PinSet, PersonalPinSetFactory(owner_id=subject_user.id))
        result_pin = cast(
            Pin,
            PinFactory(name="Search Candidate", approved=True, created_by=admin_user),
        )

        async def fake_search_pin(*, query, session):
            assert query == "search candidate"
            assert session is not None
            return [result_pin]

        monkeypatch.setattr(user_sets_module, "search_pin", fake_search_pin)
        response = auth_client_as_subject.get(
            f"/user/sets/{pin_set.id}/pin-search",
            params={"q": "search candidate"},
        )
        assert response.status_code == 200
        assert "Search Candidate" in response.text
