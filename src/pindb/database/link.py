"""External URL path strings attached to pins, shops, artists, and sets."""

from __future__ import annotations

from rich.repr import Result
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from pindb.database.audit_mixin import AuditMixin
from pindb.database.base import Base


class Link(AuditMixin, MappedAsDataclass, Base):
    """Single external hyperlink stored as a normalized path/URL string."""

    __tablename__ = "links"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        init=False,
    )

    # Required Attributes
    path: Mapped[str]

    def __hash__(self) -> int:
        return hash(self.path + str(self.id))

    def __rich_repr__(self) -> Result:
        try:
            yield "id", self.id
            yield "path", self.path
        except Exception:
            yield "detached", True
