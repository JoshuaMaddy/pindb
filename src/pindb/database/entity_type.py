from enum import StrEnum, auto

from pindb.database.artist import Artist
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.database.tag import Tag


class EntityType(StrEnum):
    pin = auto()
    shop = auto()
    artist = auto()
    tag = auto()
    pin_set = auto()

    @property
    def model(self) -> type[Pin | Shop | Artist | Tag | PinSet]:
        return _MODEL_MAP[self]


_MODEL_MAP: dict[EntityType, type[Pin | Shop | Artist | Tag | PinSet]] = {
    EntityType.pin: Pin,
    EntityType.shop: Shop,
    EntityType.artist: Artist,
    EntityType.tag: Tag,
    EntityType.pin_set: PinSet,
}
