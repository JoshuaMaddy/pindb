"""User-filed reports on content, and their admin resolution state.

Generic by design: ``target_type`` + ``target_id`` can point at anything, so the
same queue and the same admin actions extend to pins/tags/shops later without a
schema change. Only ``display_image`` is wired up today.

Deliberately **not** an :class:`AuditMixin` entity — like ``ChangeLog``, it is
excluded from the audit system. ``created_by_id`` would be a second name for
``reporter_id``, and the soft-delete/pending loader filters have nothing to say
about a report.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum, auto
from typing import TYPE_CHECKING

from rich.repr import Result
from sqlalchemy import (
    Enum as SQLAlchemyEnum,
)
from sqlalchemy import (
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)

from pindb.database.base import Base
from pindb.utils import utc_now

if TYPE_CHECKING:
    from pindb.database.user import User


class ReportTargetType(StrEnum):
    """What kind of thing a report points at.

    Kept separate from ``database/entity_type.py::EntityType``, which is tied to
    the Meilisearch index map and the editor options allowlist. A display image
    has no index and no options endpoint, so it does not belong there.
    """

    display_image = auto()
    pin = auto()
    tag = auto()
    shop = auto()
    artist = auto()
    pin_set = auto()
    user = auto()


class ReportStatus(StrEnum):
    """Where a report sits in the admin queue."""

    open = auto()
    dismissed = auto()
    actioned = auto()


# Short enough not to be a barrier to reporting something genuinely bad, long
# enough that "bad" alone doesn't reach an admin with no context.
MIN_REPORT_REASON_LENGTH: int = 10
MAX_REPORT_REASON_LENGTH: int = 1000

# See user_display.py: ``native_enum=False`` otherwise sizes the VARCHAR to the
# longest value present today, so the first new member needs a migration.
_ENUM_LENGTH: int = 32


class ContentReport(MappedAsDataclass, Base):
    """One user's report about one piece of content."""

    __tablename__ = "content_reports"
    __table_args__ = (
        # One report per user per target: free anti-spam, and a second report
        # from the same person adds nothing an admin can act on.
        UniqueConstraint(
            "reporter_id",
            "target_type",
            "target_id",
            name="uq_content_reports_reporter_target",
        ),
        Index("ix_content_reports_status_created_at", "status", "created_at"),
        Index("ix_content_reports_target", "target_type", "target_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    target_type: Mapped[ReportTargetType] = mapped_column(
        SQLAlchemyEnum(
            ReportTargetType,
            name="reporttargettype",
            native_enum=False,
            length=_ENUM_LENGTH,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
    )
    target_id: Mapped[int]
    reason: Mapped[str] = mapped_column(Text)

    # Nullable: account erasure anonymises the reporter but keeps the report —
    # an abuse report should outlive the reporter closing their account.
    reporter_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        default=None,
    )
    status: Mapped[ReportStatus] = mapped_column(
        SQLAlchemyEnum(
            ReportStatus,
            name="reportstatus",
            native_enum=False,
            length=_ENUM_LENGTH,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=ReportStatus.open,
        server_default=ReportStatus.open.value,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(default=None)
    resolved_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        default=None,
    )
    resolution_note: Mapped[str | None] = mapped_column(Text, default=None)
    # Server default (naive UTC), same as MessageReceipt and for the same reason:
    # reports are written by a Core ``INSERT ... ON CONFLICT DO NOTHING``, which
    # bypasses the ORM entirely — so ``default_factory`` never fires and this
    # NOT NULL column would land as null.
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("timezone('utc', now())"),
        default_factory=utc_now,
        init=False,
    )

    # No ``default`` on these — see the note in database/message.py: a default of
    # None makes the dataclass set the relationship, and SQLAlchemy then nulls
    # the FK column the caller set explicitly.
    reporter: Mapped[User | None] = relationship(
        foreign_keys=[reporter_id],
        init=False,
    )
    resolved_by: Mapped[User | None] = relationship(
        foreign_keys=[resolved_by_id],
        init=False,
    )

    def __hash__(self) -> int:
        return self.id or 0

    def __rich_repr__(self) -> Result:
        try:
            yield "id", self.id
            yield "target_type", self.target_type
            yield "target_id", self.target_id
            yield "status", self.status
            yield "reporter_id", self.reporter_id, None
            yield "created_at", self.created_at
        except Exception:
            yield "detached", True
