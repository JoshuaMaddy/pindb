"""Helpers for seeding pending/bulk rows in integration tests."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pindb.database.pending_edit import PendingEdit

INCLUDE_PENDING_AND_DELETED: dict[str, Any] = {
    "include_pending": True,
    "include_deleted": True,
}

INCLUDE_PENDING_ONLY: dict[str, Any] = {"include_pending": True}


def set_bulk_id(entity: object, bulk_id: UUID) -> None:
    """Attach a bulk id to a PendingMixin entity in tests."""
    setattr(entity, "bulk_id", bulk_id)


def pending_name_edit(
    *,
    entity_type: str,
    entity_id: int,
    old_name: str,
    new_name: str,
    created_by_id: int,
    bulk_id: UUID | None = None,
) -> PendingEdit:
    """Build a simple name-change PendingEdit payload row."""
    patch: dict[str, dict[str, Any]] = {
        "name": {"old": old_name, "new": new_name},
    }
    return PendingEdit(
        entity_type=entity_type,
        entity_id=entity_id,
        patch=patch,
        created_by_id=created_by_id,
        bulk_id=bulk_id,
    )
