"""User-facing messages (direct or broadcast) and per-user receipt state.

A :class:`Message` is authored by a user or the system (``sender_id`` NULL) and
targeted at one user (``recipient_id`` set) or broadcast to an audience
(``recipient_id`` NULL, filtered by ``audience``). Per-user seen/read/archived
state lives in :class:`MessageReceipt`, created lazily on first interaction — so a
broadcast has zero receipt rows until a user touches it, and the absence of a row
means "unseen, unread, not archived".
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum, auto
from typing import TYPE_CHECKING, ClassVar

from rich.repr import Result
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy import (
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)

from pindb.database.audit_mixin import AuditMixin
from pindb.database.base import Base
from pindb.database.entity_type import EntityType
from pindb.database.types import PydanticJSON
from pindb.models.message_body import MessageBody, MessageBodyAdapter
from pindb.utils import utc_now

if TYPE_CHECKING:
    from pindb.database.user import User


class MessageCategory(StrEnum):
    """Coarse message kind, used for filtering and rendering choices."""

    system = auto()
    announcement = auto()
    direct = auto()
    contribution = auto()
    pin_rejection = auto()
    # "achievement" (11 chars) fits the existing VARCHAR(13) sized to
    # "pin_rejection"; adding a member needs no migration (native_enum=False,
    # no CHECK constraint).
    achievement = auto()


class MessageAudience(StrEnum):
    """Recipient scope for a broadcast (``recipient_id IS NULL``) message."""

    all = auto()
    editors = auto()
    admins = auto()


class Message(AuditMixin, MappedAsDataclass, Base):
    """A message from a user or the system, to one user or broadcast to all."""

    __tablename__ = "messages"
    # Keep AuditMixin timestamps but write no ChangeLog rows: a change-log entry
    # would copy the (possibly private, direct) body and sender/recipient ids
    # into ``change_log.patch``, where they would outlive account erasure.
    __change_log_exclude__: ClassVar[bool] = True
    __table_args__ = (
        CheckConstraint(
            "(related_entity_type IS NULL) = (related_entity_id IS NULL)",
            name="related_entity_both_or_neither",
        ),
        Index(
            "ix_messages_recipient_active",
            "recipient_id",
            postgresql_where="deleted_at IS NULL",
        ),
        Index(
            "ix_messages_related_entity",
            "related_entity_type",
            "related_entity_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    # Required attributes
    category: Mapped[MessageCategory] = mapped_column(
        SQLAlchemyEnum(
            MessageCategory,
            name="messagecategory",
            native_enum=False,
        ),
    )
    body: Mapped[MessageBody] = mapped_column(PydanticJSON(MessageBodyAdapter))

    # Optional attributes
    sender_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        default=None,
    )
    recipient_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        default=None,
    )
    audience: Mapped[MessageAudience] = mapped_column(
        SQLAlchemyEnum(
            MessageAudience,
            name="messageaudience",
            native_enum=False,
        ),
        default=MessageAudience.all,
        server_default=MessageAudience.all.value,
    )
    related_entity_type: Mapped[EntityType | None] = mapped_column(
        SQLAlchemyEnum(
            EntityType,
            name="entitytype",
            native_enum=False,
        ),
        default=None,
    )
    related_entity_id: Mapped[int | None] = mapped_column(default=None)
    expires_at: Mapped[datetime | None] = mapped_column(default=None)
    # SET NULL so hard-deleting a thread parent (e.g. account erasure removing a
    # recipient's inbox) orphans replies instead of violating the FK.
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"),
        default=None,
    )

    # Relationships. NOTE: scalar many-to-one relationships are declared
    # ``init=False`` WITHOUT a ``default`` — giving them ``default=None`` would
    # make the dataclass set the attribute to ``None`` on construction, and
    # SQLAlchemy would then treat the (empty) relationship as authoritative and
    # null out the ``*_id`` FK column the caller set explicitly.
    sender: Mapped[User | None] = relationship(
        foreign_keys=[sender_id],
        init=False,
    )
    recipient: Mapped[User | None] = relationship(
        foreign_keys=[recipient_id],
        init=False,
    )
    parent: Mapped[Message | None] = relationship(
        remote_side=lambda: [Message.id],
        foreign_keys=[parent_id],
        init=False,
    )
    receipts: Mapped[list[MessageReceipt]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        init=False,
        default_factory=list,
        repr=False,
    )

    def __rich_repr__(self) -> Result:
        """Rich debug fields for consoles and traces."""
        try:
            yield "id", self.id
            yield "category", self.category
            yield "sender_id", self.sender_id, None
            yield "recipient_id", self.recipient_id, None
            yield "audience", self.audience, MessageAudience.all
            yield "related_entity_type", self.related_entity_type, None
            yield "expires_at", self.expires_at, None
            yield "created_at", self.created_at
        except Exception:
            yield "detached", True


class MessageReceipt(MappedAsDataclass, Base):
    """Per-(message, user) state, created lazily on first interaction.

    Deliberately omits :class:`AuditMixin` so ``user_id`` is the only foreign key
    to ``users`` (no ``foreign_keys=`` disambiguation needed) and the hot
    per-user state table stays small.
    """

    __tablename__ = "message_receipts"
    __table_args__ = (
        UniqueConstraint(
            "message_id",
            "user_id",
            name="uq_message_receipts_message_id_user_id",
        ),
        Index(
            "ix_message_receipts_user_state",
            "user_id",
            "archived_at",
            "seen_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    seen_at: Mapped[datetime | None] = mapped_column(default=None)
    read_at: Mapped[datetime | None] = mapped_column(default=None)
    archived_at: Mapped[datetime | None] = mapped_column(default=None)
    # Server default (naive UTC) so lazy Core ``INSERT ... ON CONFLICT`` upserts,
    # which bypass the ORM ``default_factory``, still populate ``created_at``.
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("timezone('utc', now())"),
        default_factory=utc_now,
        init=False,
    )

    # See the note on Message's scalar relationships: no ``default`` so the
    # explicitly-set ``message_id`` / ``user_id`` FKs are not nulled on flush.
    message: Mapped[Message] = relationship(
        back_populates="receipts",
        foreign_keys=[message_id],
        init=False,
    )
    user: Mapped[User] = relationship(
        foreign_keys=[user_id],
        init=False,
    )

    def __rich_repr__(self) -> Result:
        """Rich debug fields for consoles and traces."""
        try:
            yield "id", self.id
            yield "message_id", self.message_id
            yield "user_id", self.user_id
            yield "seen_at", self.seen_at, None
            yield "read_at", self.read_at, None
            yield "archived_at", self.archived_at, None
        except Exception:
            yield "detached", True
