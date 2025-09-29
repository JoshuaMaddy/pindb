from __future__ import annotations

from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from pindb.database.base import Base


class Link(MappedAsDataclass, Base):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        init=False,
    )

    # Required Attributes
    path: Mapped[str]

    def __hash__(self) -> int:
        return hash(self.path + str(self.id))
