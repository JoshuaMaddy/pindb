from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from rich.repr import Result
from sqlalchemy import ForeignKey
from sqlalchemy.orm import (
    Mapped,
    MappedAsDataclass,
    mapped_column,
    object_session,
    relationship,
)

from pindb.database.audit_mixin import AuditMixin
from pindb.database.base import Base
from pindb.database.pending_mixin import PendingMixin
from pindb.database.joins import (
    pin_set_memberships,
    pins_artists,
    pins_grades,
    pins_links,
    pins_shops,
    pins_tags,
)
from pindb.models import AcquisitionType, FundingType

if TYPE_CHECKING:
    from pindb.database.artist import Artist
    from pindb.database.currency import Currency
    from pindb.database.grade import Grade
    from pindb.database.link import Link
    from pindb.database.pin_set import PinSet
    from pindb.database.shop import Shop
    from pindb.database.tag import Tag


class Pin(PendingMixin, AuditMixin, MappedAsDataclass, Base):
    __tablename__ = "pins"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)

    # Required Attributes
    name: Mapped[str]
    acquisition_type: Mapped[AcquisitionType]
    front_image_guid: Mapped[UUID]
    currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id"), init=False)
    currency: Mapped[Currency] = relationship()

    # Required Relationships
    grades: Mapped[set[Grade]] = relationship(
        secondary=pins_grades,
    )
    shops: Mapped[set[Shop]] = relationship(
        secondary=pins_shops,
        back_populates="pins",
    )

    # Optional Attributes
    ## Production
    limited_edition: Mapped[bool | None] = mapped_column(default=None)
    number_produced: Mapped[int | None] = mapped_column(default=None)
    release_date: Mapped[date | None] = mapped_column(default=None)
    end_date: Mapped[date | None] = mapped_column(default=None)
    funding_type: Mapped[FundingType | None] = mapped_column(default=None)
    ## Physical
    posts: Mapped[int] = mapped_column(default=1)
    # In mm
    width: Mapped[float | None] = mapped_column(default=None)
    height: Mapped[float | None] = mapped_column(default=None)
    ## Media
    back_image_guid: Mapped[UUID | None] = mapped_column(default=None)
    ## Info
    description: Mapped[str | None] = mapped_column(default=None)
    # TODO ADD THESE TO FORM
    sku: Mapped[str | None] = mapped_column(default=None)

    # Optional Relationships
    artists: Mapped[set[Artist]] = relationship(
        secondary=pins_artists,
        back_populates="pins",
        default_factory=set,
    )
    sets: Mapped[set[PinSet]] = relationship(
        secondary=pin_set_memberships,
        back_populates="pins",
        default_factory=set,
    )
    tags: Mapped[set[Tag]] = relationship(
        secondary=pins_tags,
        back_populates="pins",
        default_factory=set,
    )
    links: Mapped[set[Link]] = relationship(
        secondary=pins_links,
        default_factory=set,
    )

    def __hash__(self) -> int:
        return hash(self.name) + (self.id or 0)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Pin):
            return False

        return value.id == self.id

    def document(self) -> dict[str, int | str | list[str]]:
        document: dict[str, int | str | list[str]] = dict()
        document.update(
            {
                "id": self.id,
                "name": self.name,
                "shops": [shop.name for shop in self.shops],
            }
        )
        document.update(
            {
                "tags": [tag.name for tag in self.tags],
            }
        ) if self.tags else None

        document.update(
            {
                "artists": [artist.name for artist in self.artists],
            }
        ) if self.artists else None

        document.update(
            {
                "description": self.description,
            }
        ) if self.description else None

        return document

    def __rich_repr__(self) -> Result:
        try:
            yield "id", self.id
            yield "name", self.name
            yield "is_pending", self.is_pending, False
            yield "acquisition_type", self.acquisition_type
            yield "posts", self.posts, 1
            yield "width", self.width, None
            yield "height", self.height, None
            yield "sku", self.sku, None
            yield "release_date", self.release_date, None
            yield "limited_edition", self.limited_edition, None
            yield "funding_type", self.funding_type, None
        except Exception:
            yield "detached", True
            return
        if object_session(self):
            yield "currency", self.currency.code
            yield "shops", self.shops, set()
            yield "grades", self.grades, set()
            yield "artists", self.artists, set()
            yield "tags", self.tags, set()
            yield "number_of_sets", len(self.sets), 0
