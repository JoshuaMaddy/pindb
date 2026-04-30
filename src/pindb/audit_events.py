"""SQLAlchemy session hooks for audit timestamps, change history, and row visibility.

Registers three listeners on SQLAlchemy's sync ``Session`` class:

* ``before_flush`` — fills ``AuditMixin`` timestamps and user ids, queues
  ``ChangeLog`` work, and auto-approves ``PendingMixin`` rows created by admins.
* ``after_flush`` — persists ``ChangeLog`` rows with JSON patches (or full
  snapshots for creates).
* ``do_orm_execute`` — applies loader criteria so soft-deleted rows and
  pending/unapproved content are hidden unless execution options opt out.

Audit user id and role flags come from ContextVars set in ``auth.attach_user_middleware``.
"""

from __future__ import annotations

import enum
from contextvars import ContextVar
from datetime import date, datetime
from typing import Any
from uuid import UUID

import sqlalchemy
from sqlalchemy import event
from sqlalchemy.orm import ORMExecuteState, Session, with_loader_criteria
from sqlalchemy.orm.attributes import get_history
from sqlalchemy.orm.state import InstanceState

from pindb.database.audit_mixin import AuditMixin
from pindb.database.pending_mixin import PendingMixin
from pindb.utils import utc_now

_AUDIT_FIELDS: frozenset[str] = frozenset(
    {
        "created_at",
        "created_by_id",
        "updated_at",
        "updated_by_id",
        "deleted_at",
        "deleted_by_id",
    }
)

_audit_user_id: ContextVar[int | None] = ContextVar("_audit_user_id", default=None)
_audit_user_is_admin: ContextVar[bool] = ContextVar(
    "_audit_user_is_admin", default=False
)
_audit_user_is_editor: ContextVar[bool] = ContextVar(
    "_audit_user_is_editor", default=False
)

# Each entry: (obj, operation, patch_or_None)
# patch=None for creates — snapshot is taken post-flush in after_flush
_pending_audit: ContextVar[list[tuple[Any, str, dict | None]] | None] = ContextVar(
    "_pending_audit", default=None
)


def set_audit_user(user_id: int | None) -> None:
    """Store the acting user id for the current async context (audit + ChangeLog).

    Args:
        user_id (int | None): Authenticated user primary key, or ``None`` for guests.
    """
    _audit_user_id.set(user_id)


def set_audit_user_flags(is_admin: bool, is_editor: bool) -> None:
    """Store role flags used by pending-content visibility in ``_filter_deleted``.

    Args:
        is_admin (bool): Whether the current user is an admin.
        is_editor (bool): Whether to use editor-style pending visibility. Callers
            typically pass ``True`` here for editors **or** admins (admins see
            pending content the same way editors do).
    """
    _audit_user_is_admin.set(is_admin)
    _audit_user_is_editor.set(is_editor)


def get_audit_user() -> int | None:
    """Return the user id last set by ``set_audit_user`` for this context.

    Returns:
        int | None: Current audit user id, or ``None`` when unset.
    """
    return _audit_user_id.get()


def _serialize_value(val: object) -> object:
    """Convert ORM values to JSON-friendly primitives for ``ChangeLog.patch``."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, UUID):
        return str(val)
    if isinstance(val, enum.Enum):
        return val.value
    return val


def _get_mapper(obj: AuditMixin) -> Any:
    """Return SQLAlchemy mapper metadata for *obj* (internal helper).

    Args:
        obj (AuditMixin): ORM instance.

    Returns:
        Mapper for the instance's mapped class.
    """
    insp: InstanceState[Any] | None = sqlalchemy.inspect(obj)  # type: ignore[assignment]
    assert insp is not None
    return insp.mapper


def _snapshot(obj: AuditMixin) -> dict:
    """Serialize all non-audit columns on *obj* for create operations."""
    mapper = _get_mapper(obj)
    return {
        col.key: _serialize_value(getattr(obj, col.key, None))
        for col in mapper.column_attrs
        if col.key not in _AUDIT_FIELDS
    }


def _compute_patch(obj: AuditMixin) -> dict:
    """Build a JSON-serializable ``{field: {old, new}}`` diff for dirty columns."""
    mapper = _get_mapper(obj)
    patch: dict = {}
    for col in mapper.column_attrs:
        if col.key in _AUDIT_FIELDS:
            continue
        hist = get_history(obj, col.key)
        if hist.deleted:
            old = hist.deleted[0] if hist.deleted else None
            new = hist.added[0] if hist.added else None
            patch[col.key] = {
                "old": _serialize_value(old),
                "new": _serialize_value(new),
            }
    return patch


def _before_flush(session: Session, flush_context: object, instances: object) -> None:
    """Apply audit timestamps and queue ``ChangeLog`` entries for this flush."""
    from pindb.database.change_log import ChangeLog

    user_id = _audit_user_id.get()
    now = utc_now()
    pending: list[tuple[Any, str, dict | None]] = _pending_audit.get() or []

    is_admin = _audit_user_is_admin.get()
    for obj in list(session.new):
        if not isinstance(obj, AuditMixin) or isinstance(obj, ChangeLog):
            continue
        obj.created_at = now
        obj.created_by_id = user_id
        obj.updated_at = now
        obj.updated_by_id = user_id
        if isinstance(obj, PendingMixin) and is_admin:
            obj.approved_at = now
            obj.approved_by_id = user_id
        # Snapshot taken post-flush (after_flush) so FKs are populated
        pending.append((obj, "create", None))

    for obj in list(session.dirty):
        if not isinstance(obj, AuditMixin) or isinstance(obj, ChangeLog):
            continue
        obj.updated_at = now
        obj.updated_by_id = user_id
        diff = _compute_patch(obj)
        # `deleted_at` is excluded from `_AUDIT_FIELDS`, so we detect a
        # soft-delete by inspecting the column transition directly.
        deleted_hist = get_history(obj, "deleted_at")
        added = list(deleted_hist.added or ())
        deleted = list(deleted_hist.deleted or ())
        new_deleted_at = added[0] if added else None
        old_deleted_at = deleted[0] if deleted else None
        became_deleted = new_deleted_at is not None and old_deleted_at is None
        if became_deleted:
            diff["deleted_at"] = {
                "old": _serialize_value(old_deleted_at),
                "new": _serialize_value(new_deleted_at),
            }
            pending.append((obj, "delete", diff))
        elif diff:
            pending.append((obj, "update", diff))

    _pending_audit.set(pending)


def _after_flush(session: Session, flush_context: object) -> None:
    """Persist ``ChangeLog`` rows for operations queued in ``_before_flush``."""
    from pindb.database.change_log import ChangeLog

    pending = _pending_audit.get()
    if not pending:
        return
    # Clear before processing — prevents double-emit on the second flush
    _pending_audit.set([])

    user_id = _audit_user_id.get()
    for obj, operation, patch in pending:
        resolved_patch = _snapshot(obj) if patch is None else patch
        log = ChangeLog(
            entity_type=obj.__tablename__,
            entity_id=obj.id,
            operation=operation,
            changed_by_id=user_id,
            patch=resolved_patch,
        )
        session.add(log)


def _filter_deleted(execute_state: ORMExecuteState) -> None:
    """Hide soft-deleted and (for most users) unapproved rows from SELECTs.

    Honors ``execution_options(include_deleted=True)`` and
    ``include_pending=True`` for admin approval views.
    """
    if not execute_state.is_select:
        return

    if not execute_state.execution_options.get("include_deleted", False):
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                AuditMixin,
                lambda cls: cls.deleted_at.is_(None),
                include_aliases=True,
            )
        )

    if not execute_state.execution_options.get("include_pending", False):
        if _audit_user_is_editor.get():
            # Editors see approved + pending, not rejected
            execute_state.statement = execute_state.statement.options(
                with_loader_criteria(
                    PendingMixin,
                    lambda cls: cls.rejected_at.is_(None),
                    include_aliases=True,
                )
            )
        else:
            # Regular users and guests see only approved items
            execute_state.statement = execute_state.statement.options(
                with_loader_criteria(
                    PendingMixin,
                    lambda cls: (
                        cls.approved_at.is_not(None) & cls.rejected_at.is_(None)
                    ),
                    include_aliases=True,
                )
            )


def register_audit_events() -> None:
    """Attach audit and visibility listeners to every ORM session."""
    if not event.contains(Session, "before_flush", _before_flush):
        event.listen(Session, "before_flush", _before_flush)
    if not event.contains(Session, "after_flush", _after_flush):
        event.listen(Session, "after_flush", _after_flush)
    if not event.contains(Session, "do_orm_execute", _filter_deleted):
        event.listen(Session, "do_orm_execute", _filter_deleted)
