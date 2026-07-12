"""
FastAPI routes: `routes/_guards.py`.
"""

from fastapi import HTTPException

from pindb.database.pending_mixin import PendingAuditEntity
from pindb.database.user import User


def assert_editor_can_edit(entity: PendingAuditEntity, current_user: User) -> None:
    """Raise 403 if a non-admin editor cannot edit the given entity.

    Editors may:
    - Edit approved entities (the edit is captured as a pending edit instead
      of a direct mutation — see needs_pending_edit()).
    - Edit their own unapproved entries directly. That covers both pending
      entries and needs-changes ones: acting on a reviewer's feedback *is* the
      point of the needs-changes state, so the submitter must be able to edit.

    Admins bypass all checks.
    """
    if current_user.is_admin:
        return
    if entity.is_approved:
        return
    if entity.created_by_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Can only edit your own pending entries"
        )


def clear_rejection(entity: PendingAuditEntity) -> None:
    """Clear the needs-changes flag, returning the entry to the pending queue."""
    entity.rejected_at = None
    entity.rejected_by_id = None
    entity.rejection_reason = None


def clear_rejection_on_resubmit(entity: PendingAuditEntity, current_user: User) -> None:
    """Send a needs-changes entry back to pending when its submitter edits it.

    Acting on the reviewer's feedback is what the needs-changes state asks for,
    so a direct edit by the submitter counts as a resubmission and puts the entry
    back in front of an admin. The notification ``Message`` stays in their inbox
    as the paper trail.

    An admin editing a needs-changes entry does not clear it — they can approve
    it outright, and silently un-flagging on every admin touch would lose the
    reviewer's decision.
    """
    if current_user.is_admin or not entity.is_rejected:
        return
    clear_rejection(entity)


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
