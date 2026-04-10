from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from rich.repr import Result
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
    object_session,
    relationship,
)

from pindb.database.base import Base

if TYPE_CHECKING:
    from pindb.database.user import User


class UserSession(MappedAsDataclass, Base):
    __tablename__ = "user_sessions"

    token: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime]
    created_at: Mapped[datetime] = mapped_column(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        init=False,
    )

    user: Mapped[User] = relationship(back_populates="sessions", init=False)

    def __rich_repr__(self) -> Result:
        yield "user_id", self.user_id
        yield "expires_at", self.expires_at
        yield "created_at", self.created_at
        if object_session(self):
            yield "username", self.user.username
        else:
            yield "session", "expired"
