from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from rich.repr import Result
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from pindb.database.audit_mixin import AuditMixin
from pindb.database.base import Base

if TYPE_CHECKING:
    from pindb.database.user import User


class OAuthProvider(StrEnum):
    google = "google"
    discord = "discord"


class UserAuthProvider(AuditMixin, MappedAsDataclass, Base):
    __tablename__ = "user_auth_providers"
    __table_args__ = (UniqueConstraint("provider", "provider_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    provider: Mapped[OAuthProvider]
    provider_user_id: Mapped[str]
    provider_email: Mapped[str | None] = mapped_column(default=None)

    user: Mapped[User] = relationship(
        back_populates="auth_providers", init=False, foreign_keys=[user_id]
    )

    def __rich_repr__(self) -> Result:
        try:
            yield "id", self.id
            yield "user_id", self.user_id
            yield "provider", self.provider
            yield "provider_user_id", self.provider_user_id
            yield "provider_email", self.provider_email, None
        except Exception:
            yield "detached", True
