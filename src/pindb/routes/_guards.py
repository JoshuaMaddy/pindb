from fastapi import HTTPException

from pindb.database.pending_mixin import PendingAuditEntity
from pindb.database.user import User


def assert_editor_can_edit(entity: PendingAuditEntity, current_user: User) -> None:
    """Raise 403 if a non-admin editor cannot edit the given entity.

    Editors may:
    - Edit approved entities (the edit is captured as a pending edit instead
      of a direct mutation — see needs_pending_edit()).
    - Edit their own unapproved pending-new entries directly.

    Admins bypass all checks.
    """
    if current_user.is_admin:
        return
    if entity.is_approved:
        return
    if entity.is_rejected:
        raise HTTPException(status_code=403, detail="Cannot edit rejected entries")
    if entity.created_by_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Can only edit your own pending entries"
        )


def needs_pending_edit(entity: PendingAuditEntity, current_user: User) -> bool:
    """True if this edit should be stored as a PendingEdit rather than a
    direct mutation of the canonical row.

    Editors editing an already-approved entity go through the pending edit
    flow. Admins always edit directly. Editors editing their own pending-new
    entry edit directly.
    """
    if current_user.is_admin:
        return False
    return entity.is_approved
