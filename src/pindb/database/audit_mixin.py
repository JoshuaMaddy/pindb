"""Reusable audit columns: who created/updated/deleted rows and when."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from pindb.utils import utc_now


class AuditMixin(MappedAsDataclass):
    """Soft-delete and audit metadata mixed into most persisted entities."""

    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        default_factory=utc_now,
        init=False,
    )
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        default=None,
        init=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        default=None,
        init=False,
    )
    updated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        default=None,
        init=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        default=None,
        init=False,
    )
    deleted_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        default=None,
        init=False,
    )
