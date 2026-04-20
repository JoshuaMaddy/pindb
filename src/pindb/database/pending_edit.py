"""Admin-reviewable proposed edits to canonical entities (patch chains)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from rich.repr import Result
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from pindb.database.base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PendingEdit(MappedAsDataclass, Base):
    """Proposed edit to a canonical entity, awaiting admin approval.

    entity_type is the table name of the target entity (e.g. "pins").
    patch is a flat dict of {field_name: {"old": ..., "new": ...}}.
    parent_id links edits in a chain so they can stack on top of each other.
    """

    __tablename__ = "pending_edits"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    entity_type: Mapped[str]
    entity_id: Mapped[int]
    patch: Mapped[dict] = mapped_column(JSONB, default_factory=dict)

    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(default_factory=_utc_now, init=False)

    approved_at: Mapped[datetime | None] = mapped_column(default=None)
    approved_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), default=None
    )
    rejected_at: Mapped[datetime | None] = mapped_column(default=None)
    rejected_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), default=None
    )

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("pending_edits.id"), default=None
    )
    bulk_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        default=None,
        index=True,
    )

    @property
    def is_pending(self) -> bool:
        return self.approved_at is None and self.rejected_at is None

    @property
    def is_approved(self) -> bool:
        return self.approved_at is not None

    @property
    def is_rejected(self) -> bool:
        return self.rejected_at is not None

    def __rich_repr__(self) -> Result:
        """Rich debug fields for consoles and traces."""
        try:
            yield "id", self.id
            yield "entity_type", self.entity_type
            yield "entity_id", self.entity_id
            yield "created_at", self.created_at
            yield "created_by_id", self.created_by_id, None
            yield "approved_at", self.approved_at, None
            yield "rejected_at", self.rejected_at, None
            yield "parent_id", self.parent_id, None
        except Exception:
            yield "detached", True
