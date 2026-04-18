from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column


class PendingAuditEntity(Protocol):
    """Protocol describing entities that have both PendingMixin and AuditMixin fields."""

    id: int
    created_by_id: int | None
    created_at: datetime
    deleted_at: datetime | None
    approved_at: datetime | None
    approved_by_id: int | None
    rejected_at: datetime | None
    rejected_by_id: int | None
    bulk_id: UUID | None

    @property
    def is_pending(self) -> bool: ...

    @property
    def is_approved(self) -> bool: ...

    @property
    def is_rejected(self) -> bool: ...


class PendingMixin(MappedAsDataclass):
    __abstract__ = True

    approved_at: Mapped[datetime | None] = mapped_column(
        default=None,
        init=False,
    )
    approved_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        default=None,
        init=False,
    )
    rejected_at: Mapped[datetime | None] = mapped_column(
        default=None,
        init=False,
    )
    rejected_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        default=None,
        init=False,
    )
    bulk_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        default=None,
        init=False,
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
