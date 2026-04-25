"""Registered user accounts: credentials, OAuth links, favorites, and pin lists."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.repr import Result
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
    object_session,
    relationship,
)

from pindb.database.audit_mixin import AuditMixin
from pindb.database.base import Base
from pindb.database.joins import user_favorite_pin_sets, user_favorite_pins

if TYPE_CHECKING:
    from pindb.database.pin import Pin
    from pindb.database.pin_set import PinSet
    from pindb.database.session import UserSession
    from pindb.database.user_auth_provider import UserAuthProvider
    from pindb.database.user_owned_pin import UserOwnedPin
    from pindb.database.user_wanted_pin import UserWantedPin


class User(AuditMixin, MappedAsDataclass, Base):
    """Application user with roles, theme, units prefs, and pin relationships."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str | None] = mapped_column(unique=True, default=None)
    hashed_password: Mapped[str | None] = mapped_column(default=None)
    is_admin: Mapped[bool] = mapped_column(default=False)
    is_editor: Mapped[bool] = mapped_column(default=False)
    theme: Mapped[str] = mapped_column(default="mocha", server_default="mocha")
    dimension_unit: Mapped[str] = mapped_column(default="mm", server_default="mm")

    sessions: Mapped[list[UserSession]] = relationship(
        back_populates="user",
        default_factory=list,
        cascade="all, delete-orphan",
        repr=False,
    )
    auth_providers: Mapped[list[UserAuthProvider]] = relationship(
        back_populates="user",
        default_factory=list,
        cascade="all, delete-orphan",
        foreign_keys="[UserAuthProvider.user_id]",
    )
    favorite_pins: Mapped[set[Pin]] = relationship(
        secondary=user_favorite_pins,
        default_factory=set,
    )
    favorite_pin_sets: Mapped[set[PinSet]] = relationship(
        secondary=user_favorite_pin_sets,
        default_factory=set,
    )
    personal_sets: Mapped[list[PinSet]] = relationship(
        back_populates="owner",
        default_factory=list,
        foreign_keys="PinSet.owner_id",
    )
    owned_pins: Mapped[list[UserOwnedPin]] = relationship(
        back_populates="user",
        default_factory=list,
        cascade="all, delete-orphan",
        foreign_keys="[UserOwnedPin.user_id]",
    )
    wanted_pins: Mapped[list[UserWantedPin]] = relationship(
        back_populates="user",
        default_factory=list,
        cascade="all, delete-orphan",
        foreign_keys="[UserWantedPin.user_id]",
    )

    def __hash__(self) -> int:
        return self.id or 0

    def __rich_repr__(self) -> Result:
        """Rich debug summary; includes related counts when session-bound."""
        try:
            yield "id", self.id
            yield "username", self.username
            yield "email", self.email, None
            yield "is_admin", self.is_admin, False
            yield "is_editor", self.is_editor, False
            yield "theme", self.theme, "mocha"
            yield "dimension_unit", self.dimension_unit, "mm"
            yield "created_at", self.created_at
        except Exception:
            yield "detached", True
            return
        if object_session(self):
            yield "auth_providers", [p.provider for p in self.auth_providers], []
            yield "number_of_favorites", len(self.favorite_pins), 0
            yield "number_of_personal_sets", len(self.personal_sets), 0
