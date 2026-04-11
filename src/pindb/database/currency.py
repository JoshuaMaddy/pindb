from __future__ import annotations

from rich.repr import Result
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from pindb.database.audit_mixin import AuditMixin
from pindb.database.base import Base


class Currency(AuditMixin, MappedAsDataclass, Base):
    __tablename__ = "currencies"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Required Attributes
    name: Mapped[str]
    code: Mapped[str]

    def __hash__(self) -> int:
        return hash(self.code)

    def __rich_repr__(self) -> Result:
        try:
            yield "id", self.id
            yield "name", self.name
            yield "code", self.code
        except Exception:
            yield "detached", True
