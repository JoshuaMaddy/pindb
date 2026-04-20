"""Maps entity kinds to ORM models and SQL table names (pending edits, search, admin)."""

from enum import StrEnum, auto

from pindb.database.artist import Artist
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.database.tag import Tag


class EntityType(StrEnum):
    """Canonical entity kinds that participate in approval and bulk workflows."""

    pin = auto()
    shop = auto()
    artist = auto()
    tag = auto()
    pin_set = auto()

    @property
    def model(self) -> type[Pin | Shop | Artist | Tag | PinSet]:
        """ORM class backing this entity kind."""
        return _MODEL_MAP[self]

    @property
    def table_name(self) -> str:
        """``__tablename__`` for the mapped entity."""
        return self.model.__tablename__

    @property
    def slug(self) -> str:
        """URL-safe enum value (same as ``.value``)."""
        return self.value

    @classmethod
    def from_table_name(cls, table_name: str) -> "EntityType | None":
        """Resolve from a SQL table name, or ``None`` if unknown."""
        return _TABLE_NAME_MAP.get(table_name)


_MODEL_MAP: dict[EntityType, type[Pin | Shop | Artist | Tag | PinSet]] = {
    EntityType.pin: Pin,
    EntityType.shop: Shop,
    EntityType.artist: Artist,
    EntityType.tag: Tag,
    EntityType.pin_set: PinSet,
}


_TABLE_NAME_MAP: dict[str, EntityType] = {
    entity_type.table_name: entity_type for entity_type in EntityType
}
