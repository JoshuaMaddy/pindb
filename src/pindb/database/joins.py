"""SQLAlchemy ``Table`` association objects (many-to-many, excluded from audit).

Each pin-facing join table carries an index on its *non-pin* column. The composite
primary key leads with ``pin_id``, so it cannot serve the "which pins belong to
this tag/shop/artist/set" direction — which is the one every list page, detail
page, and preview loader queries. Without these, those all sequential-scan the
join table.
"""

from sqlalchemy import CheckConstraint, Column, ForeignKey, Index, Integer, Table

from pindb.database.base import Base

pins_shops = Table(
    "pins_shops",
    Base.metadata,
    Column("pin_id", Integer, ForeignKey("pins.id"), primary_key=True),
    Column("shop_id", Integer, ForeignKey("shops.id"), primary_key=True),
    Index("ix_pins_shops_shop_id", "shop_id"),
)

pins_artists = Table(
    "pins_artists",
    Base.metadata,
    Column("pin_id", Integer, ForeignKey("pins.id"), primary_key=True),
    Column("artists_id", Integer, ForeignKey("artists.id"), primary_key=True),
    Index("ix_pins_artists_artists_id", "artists_id"),
)

pin_set_memberships = Table(
    "pin_set_memberships",
    Base.metadata,
    Column("pin_id", Integer, ForeignKey("pins.id"), primary_key=True),
    Column("set_id", Integer, ForeignKey("pin_sets.id"), primary_key=True),
    Column("position", Integer, nullable=False, server_default="0"),
    Index("ix_pin_set_memberships_set_id", "set_id"),
)

pins_tags = Table(
    "pins_tags",
    Base.metadata,
    Column("pin_id", Integer, ForeignKey("pins.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
    Column("implied_by_tag_id", Integer, ForeignKey("tags.id"), nullable=True),
    Index("ix_pins_tags_tag_id", "tag_id"),
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
    Column(
        "tag_id",
        Integer,
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "implied_tag_id",
        Integer,
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

display_image_pins = Table(
    "display_image_pins",
    Base.metadata,
    Column(
        "display_image_id",
        Integer,
        ForeignKey("user_display_images.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("pin_id", Integer, ForeignKey("pins.id"), primary_key=True),
    Index("ix_display_image_pins_pin_id", "pin_id"),
)

pin_variants = Table(
    "pin_variants",
    Base.metadata,
    Column("pin_id", Integer, ForeignKey("pins.id"), primary_key=True),
    Column("variant_pin_id", Integer, ForeignKey("pins.id"), primary_key=True),
    CheckConstraint("pin_id <> variant_pin_id", name="pin_variants_no_self"),
)

pin_unauthorized_copies = Table(
    "pin_unauthorized_copies",
    Base.metadata,
    Column("pin_id", Integer, ForeignKey("pins.id"), primary_key=True),
    Column("copy_pin_id", Integer, ForeignKey("pins.id"), primary_key=True),
    CheckConstraint("pin_id <> copy_pin_id", name="pin_unauthorized_copies_no_self"),
)
