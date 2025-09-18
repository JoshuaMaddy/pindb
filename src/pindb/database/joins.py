from sqlalchemy import Column, ForeignKey, Integer, Table

from pindb.database.base import Base

pins_materials = Table(
    "pins_materials",
    Base.metadata,
    Column("pin_id", Integer, ForeignKey("pins.id"), primary_key=True),
    Column("material_id", Integer, ForeignKey("materials.id"), primary_key=True),
)

pins_shops = Table(
    "pins_shops",
    Base.metadata,
    Column("pin_id", Integer, ForeignKey("pins.id"), primary_key=True),
    Column("shop_id", Integer, ForeignKey("shops.id"), primary_key=True),
)

pins_artists = Table(
    "pins_artists",
    Base.metadata,
    Column("pin_id", Integer, ForeignKey("pins.id"), primary_key=True),
    Column("artists_id", Integer, ForeignKey("artists.id"), primary_key=True),
)

pins_sets = Table(
    "pins_sets",
    Base.metadata,
    Column("pin_id", Integer, ForeignKey("pins.id"), primary_key=True),
    Column("sets_id", Integer, ForeignKey("pin_sets.id"), primary_key=True),
)

pins_tags = Table(
    "pins_tags",
    Base.metadata,
    Column("pin_id", Integer, ForeignKey("pins.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)

shops_links = Table(
    "shops_links",
    Base.metadata,
    Column("shop_id", Integer, ForeignKey("shops.id"), primary_key=True),
    Column("link_id", Integer, ForeignKey("links.id"), primary_key=True),
)

artists_links = Table(
    "artists_links",
    Base.metadata,
    Column("artist_id", Integer, ForeignKey("artists.id"), primary_key=True),
    Column("link_id", Integer, ForeignKey("links.id"), primary_key=True),
)

pin_sets_links = Table(
    "pin_sets_links",
    Base.metadata,
    Column("pin_set_id", Integer, ForeignKey("pin_sets.id"), primary_key=True),
    Column("link_id", Integer, ForeignKey("links.id"), primary_key=True),
)

pins_links = Table(
    "pins_links",
    Base.metadata,
    Column("pin_id", Integer, ForeignKey("pins.id"), primary_key=True),
    Column("link_id", Integer, ForeignKey("links.id"), primary_key=True),
)
