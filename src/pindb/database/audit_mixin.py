from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AuditMixin(MappedAsDataclass):
    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        default_factory=_utc_now,
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
