"""Low-level tests for `audit_events._filter_deleted`.

Verifies that SELECTs issued against `AuditMixin`/`PendingMixin` entities are
auto-filtered to hide soft-deleted and pending rows, and that the
`include_deleted` / `include_pending` execution options bypass those filters.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select

from pindb.audit_events import set_audit_user, set_audit_user_flags
from pindb.database import Shop
from tests.factories.shop import ShopFactory
from tests.fixtures.users import SUBJECT_USER_PARAMS


@pytest.fixture
def approved_shop(db_session, admin_user):
    shop = ShopFactory(name="Approved Shop", approved=True, created_by=admin_user)
    db_session.flush()
    return shop


@pytest.fixture
def pending_shop(db_session, editor_user):
    shop = ShopFactory(name="Pending Shop", approved=False, created_by=editor_user)
    db_session.flush()
    return shop


@pytest.fixture
def rejected_shop(db_session, editor_user, admin_user):
    shop = ShopFactory(name="Rejected Shop", approved=False, created_by=editor_user)
    shop.rejected_at = datetime.now().replace(microsecond=0)  # ty:ignore[unresolved-attribute]
    shop.rejected_by_id = admin_user.id  # ty:ignore[unresolved-attribute]
    db_session.flush()
    return shop


@pytest.fixture
def deleted_shop(db_session, admin_user):
    shop = ShopFactory(name="Deleted Shop", approved=True, created_by=admin_user)
    shop.deleted_at = datetime.now().replace(microsecond=0)  # ty:ignore[unresolved-attribute]
    shop.deleted_by_id = admin_user.id  # ty:ignore[unresolved-attribute]
    db_session.flush()
    return shop


def _names(db_session) -> set[str]:
    return set(db_session.scalars(select(Shop.name)).all())


def _names_with_opts(db_session, **opts) -> set[str]:
    return set(db_session.scalars(select(Shop.name).execution_options(**opts)).all())


@pytest.mark.integration
class TestSoftDeleteFilter:
    def test_guest_sees_only_approved_non_deleted(
        self, db_session, approved_shop, pending_shop, rejected_shop, deleted_shop
    ):
        set_audit_user(None)
        set_audit_user_flags(is_admin=False, is_editor=False)

        names = _names(db_session)
        assert "Approved Shop" in names
        assert "Pending Shop" not in names
        assert "Rejected Shop" not in names
        assert "Deleted Shop" not in names

    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_regular_user_hides_pending(
        self, db_session, subject_user, approved_shop, pending_shop
    ):
        set_audit_user(subject_user.id)
        set_audit_user_flags(is_admin=False, is_editor=False)

        names = _names(db_session)
        assert "Approved Shop" in names
        assert "Pending Shop" not in names

    def test_editor_sees_pending_but_not_rejected(
        self,
        db_session,
        editor_user,
        approved_shop,
        pending_shop,
        rejected_shop,
    ):
        set_audit_user(editor_user.id)
        set_audit_user_flags(is_admin=False, is_editor=True)

        names = _names(db_session)
        assert "Approved Shop" in names
        assert "Pending Shop" in names
        assert "Rejected Shop" not in names

    def test_admin_matches_regular_user_visibility_by_default(
        self,
        db_session,
        admin_user,
        approved_shop,
        pending_shop,
        rejected_shop,
    ):
        # Admin flags do NOT grant editor visibility automatically — admins must
        # opt into include_pending (or flip the editor flag, which admin middleware does).
        set_audit_user(admin_user.id)
        set_audit_user_flags(is_admin=True, is_editor=False)

        names = _names(db_session)
        assert "Approved Shop" in names
        assert "Pending Shop" not in names
        assert "Rejected Shop" not in names


@pytest.mark.integration
class TestBypassOptions:
    def test_include_deleted_reveals_soft_deleted_rows(
        self, db_session, admin_user, approved_shop, deleted_shop
    ):
        set_audit_user(admin_user.id)
        set_audit_user_flags(is_admin=True, is_editor=True)

        names = _names_with_opts(db_session, include_deleted=True)
        assert "Approved Shop" in names
        assert "Deleted Shop" in names

    def test_include_pending_reveals_pending_and_rejected(
        self, db_session, admin_user, approved_shop, pending_shop, rejected_shop
    ):
        set_audit_user(admin_user.id)
        set_audit_user_flags(is_admin=True, is_editor=True)

        names = _names_with_opts(db_session, include_pending=True)
        assert "Approved Shop" in names
        assert "Pending Shop" in names
        assert "Rejected Shop" in names

    def test_include_both_reveals_everything(
        self,
        db_session,
        admin_user,
        approved_shop,
        pending_shop,
        rejected_shop,
        deleted_shop,
    ):
        set_audit_user(admin_user.id)
        set_audit_user_flags(is_admin=True, is_editor=True)

        names = _names_with_opts(db_session, include_deleted=True, include_pending=True)
        assert {
            "Approved Shop",
            "Pending Shop",
            "Rejected Shop",
            "Deleted Shop",
        }.issubset(names)

    def test_default_query_still_filters_when_options_absent(
        self, db_session, admin_user, approved_shop, pending_shop, deleted_shop
    ):
        set_audit_user(admin_user.id)
        set_audit_user_flags(is_admin=True, is_editor=True)

        # Even as admin/editor, the default query should hide soft-deleted rows.
        names = _names(db_session)
        assert "Approved Shop" in names
        assert "Deleted Shop" not in names
