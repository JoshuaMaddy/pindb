"""ChangeLog is written by `audit_events._after_flush` on every create/update/
soft-delete of an AuditMixin entity. These tests verify the patches emitted."""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select

from pindb.audit_events import set_audit_user, set_audit_user_flags
from pindb.database.change_log import ChangeLog
from tests.factories.shop import ShopFactory


def _logs_for_shop(db_session, shop_id: int) -> list[ChangeLog]:
    return list(
        db_session.scalars(
            select(ChangeLog)
            .where(
                ChangeLog.entity_type == "shops",
                ChangeLog.entity_id == shop_id,
            )
            .order_by(ChangeLog.id.asc())
        ).all()
    )


@pytest.mark.integration
class TestChangeLogCreate:
    def test_create_emits_full_snapshot(self, db_session, admin_user):
        set_audit_user(admin_user.id)
        set_audit_user_flags(is_admin=True, is_editor=False)

        shop = ShopFactory(name="Log Me", approved=True, created_by=admin_user)
        db_session.flush()

        logs = _logs_for_shop(db_session, shop.id)  # ty:ignore[unresolved-attribute]
        create_logs = [log for log in logs if log.operation == "create"]
        assert len(create_logs) == 1
        log = create_logs[0]
        assert log.changed_by_id == admin_user.id
        # The create patch is a full snapshot, not old/new pairs.
        assert log.patch.get("name") == "Log Me"
        assert "id" in log.patch
        # Audit fields must not leak into the patch.
        for field in (
            "created_at",
            "created_by_id",
            "updated_at",
            "updated_by_id",
            "deleted_at",
            "deleted_by_id",
        ):
            assert field not in log.patch


@pytest.mark.integration
class TestChangeLogUpdate:
    def test_update_emits_old_new_pairs_for_changed_fields_only(
        self, db_session, admin_user
    ):
        set_audit_user(admin_user.id)
        set_audit_user_flags(is_admin=True, is_editor=False)

        shop = ShopFactory(name="Before", approved=True, created_by=admin_user)
        db_session.flush()
        create_log_count = len(_logs_for_shop(db_session, shop.id))  # ty:ignore[unresolved-attribute]

        shop.name = "After"  # ty:ignore[invalid-assignment]
        db_session.flush()

        logs = _logs_for_shop(db_session, shop.id)  # ty:ignore[unresolved-attribute]
        assert len(logs) == create_log_count + 1
        update_log = logs[-1]
        assert update_log.operation == "update"
        assert update_log.changed_by_id == admin_user.id
        assert update_log.patch == {"name": {"old": "Before", "new": "After"}}

    def test_no_op_save_emits_no_log(self, db_session, admin_user):
        set_audit_user(admin_user.id)
        set_audit_user_flags(is_admin=True, is_editor=False)

        shop = ShopFactory(name="Stable", approved=True, created_by=admin_user)
        db_session.flush()
        before = len(_logs_for_shop(db_session, shop.id))  # ty:ignore[unresolved-attribute]

        # Touch without changing anything meaningful.
        db_session.add(shop)
        db_session.flush()

        after = len(_logs_for_shop(db_session, shop.id))  # ty:ignore[unresolved-attribute]
        assert after == before


@pytest.mark.integration
class TestChangeLogDelete:
    def test_soft_delete_emits_delete_operation(self, db_session, admin_user):
        """A soft-delete (deleted_at None → not None) emits one delete log."""
        set_audit_user(admin_user.id)
        set_audit_user_flags(is_admin=True, is_editor=False)

        shop = ShopFactory(name="Delete Me", approved=True, created_by=admin_user)
        db_session.flush()
        before = _logs_for_shop(db_session, shop.id)  # ty:ignore[unresolved-attribute]

        shop.deleted_at = datetime.now().replace(microsecond=0)  # ty:ignore[unresolved-attribute]
        shop.deleted_by_id = admin_user.id  # ty:ignore[unresolved-attribute]
        db_session.flush()

        after = _logs_for_shop(db_session, shop.id)  # ty:ignore[unresolved-attribute]
        new_logs = after[len(before) :]
        delete_logs = [log for log in new_logs if log.operation == "delete"]
        assert len(delete_logs) == 1
        patch = delete_logs[0].patch
        assert "deleted_at" in patch
        assert patch["deleted_at"]["old"] is None
        assert patch["deleted_at"]["new"] is not None
