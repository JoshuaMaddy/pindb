from fastapi import HTTPException

from pindb.database.pending_mixin import PendingAuditEntity
from pindb.database.user import User


def assert_editor_can_edit(entity: PendingAuditEntity, current_user: User) -> None:
    """Raise 403 if a non-admin editor cannot edit the given entity.

    Editors may only edit their own pending (not yet approved/rejected) entries.
    Admins bypass all checks.
    """
    if current_user.is_admin:
        return
    if not entity.is_pending:
        raise HTTPException(status_code=403, detail="Can only edit pending entries")
    if entity.created_by_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Can only edit your own pending entries"
        )
