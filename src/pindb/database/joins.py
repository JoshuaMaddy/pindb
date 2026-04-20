"""SQLAlchemy ``Table`` association objects (many-to-many, excluded from audit)."""

from sqlalchemy import Column, ForeignKey, Integer, Table

from pindb.database.base import Base

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

pin_set_memberships = Table(
    "pin_set_memberships",
    Base.metadata,
    Column("pin_id", Integer, ForeignKey("pins.id"), primary_key=True),
    Column("set_id", Integer, ForeignKey("pin_sets.id"), primary_key=True),
    Column("position", Integer, nullable=False, server_default="0"),
)

pins_tags = Table(
    "pins_tags",
    Base.metadata,
    Column("pin_id", Integer, ForeignKey("pins.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
    Column("implied_by_tag_id", Integer, ForeignKey("tags.id"), nullable=True),
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

pins_grades = Table(
    "pins_grades",
    Base.metadata,
    Column("pin_id", Integer, ForeignKey("pins.id"), primary_key=True),
    Column("grade_id", Integer, ForeignKey("grades.id"), primary_key=True),
)

user_favorite_pins = Table(
    "user_favorite_pins",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("pin_id", Integer, ForeignKey("pins.id"), primary_key=True),
)

user_favorite_pin_sets = Table(
    "user_favorite_pin_sets",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("pin_set_id", Integer, ForeignKey("pin_sets.id"), primary_key=True),
)

tag_implications = Table(
    "tag_implications",
    Base.metadata,
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
    Column("implied_tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)
