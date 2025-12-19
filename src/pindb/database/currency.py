from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from pindb.database.base import Base

if TYPE_CHECKING:
    pass


class Currency(MappedAsDataclass, Base):
    __tablename__ = "currencies"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Required Attributes
    name: Mapped[str]
    code: Mapped[str]
