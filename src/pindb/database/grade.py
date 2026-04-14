from __future__ import annotations

from rich.repr import Result
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from pindb.database.audit_mixin import AuditMixin
from pindb.database.base import Base


class Grade(AuditMixin, MappedAsDataclass, Base):
    __tablename__ = "grades"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    # Required Attributes
    name: Mapped[str]
    price: Mapped[float | None] = mapped_column(default=None)

    def __hash__(self) -> int:
        return hash(self.name + str(self.id))

    def __rich_repr__(self) -> Result:
        try:
            yield "id", self.id
            yield "name", self.name
            yield "price", self.price
        except Exception:
            yield "detached", True
