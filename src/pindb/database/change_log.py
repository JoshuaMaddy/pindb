from __future__ import annotations

from datetime import datetime, timezone

from rich.repr import Result
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from pindb.database.base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ChangeLog(MappedAsDataclass, Base):
    __tablename__ = "change_log"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    entity_type: Mapped[str]
    entity_id: Mapped[int]
    operation: Mapped[str]
    changed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), default=None
    )
    changed_at: Mapped[datetime] = mapped_column(default_factory=_utc_now, init=False)
    patch: Mapped[dict] = mapped_column(JSONB, default_factory=dict)

    def __rich_repr__(self) -> Result:
        try:
            yield "id", self.id
            yield "entity_type", self.entity_type
            yield "entity_id", self.entity_id
            yield "operation", self.operation
            yield "changed_at", self.changed_at
        except Exception:
            yield "detached", True
