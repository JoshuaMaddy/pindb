from __future__ import annotations

from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from pindb.database.base import Base


class Grade(MappedAsDataclass, Base):
    __tablename__ = "grades"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    # Required Attributes
    name: Mapped[str]
    price: Mapped[float]

    def __hash__(self) -> int:
        return hash(self.name + str(self.id))
