"""SQLAlchemy engine, ``session_maker``, ORM exports, and currency seeding."""

from pathlib import Path

import polars as pl
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker as SessionMaker
from sqlalchemy.orm.session import Session, sessionmaker

from pindb.config import CONFIGURATION
from pindb.database.artist import Artist, ArtistAlias
from pindb.database.audit_mixin import AuditMixin
from pindb.database.base import Base
from pindb.database.change_log import ChangeLog
from pindb.database.currency import Currency
from pindb.database.entity_type import EntityType
from pindb.database.grade import Grade
from pindb.database.link import Link
from pindb.database.pending_edit import PendingEdit
from pindb.database.pending_mixin import PendingMixin
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.session import UserSession
from pindb.database.shop import Shop, ShopAlias
from pindb.database.tag import Tag, TagAlias, TagCategory
from pindb.database.user import User
from pindb.database.user_auth_provider import UserAuthProvider
from pindb.database.user_owned_pin import UserOwnedPin
from pindb.database.user_wanted_pin import UserWantedPin

__all__: list[str] = [
    "seed_currencies",
    "Artist",
    "ArtistAlias",
    "EntityType",
    "AuditMixin",
    "PendingMixin",
    "Base",
    "ChangeLog",
    "Currency",
    "Grade",
    "Link",
    "PendingEdit",
    "Pin",
    "PinSet",
    "Shop",
    "ShopAlias",
    "Tag",
    "TagAlias",
    "TagCategory",
    "User",
    "UserAuthProvider",
    "UserOwnedPin",
    "UserSession",
    "UserWantedPin",
]

# Create engine
__engine: Engine = create_engine(CONFIGURATION.database_connection)

# Expose sessionmaker
session_maker: sessionmaker[Session] = SessionMaker(
    bind=__engine, expire_on_commit=False
)


def seed_currencies() -> None:
    """Insert ISO currency rows from ``database/data/currencies.csv`` if missing.

    Idempotent: skips rows whose primary key already exists.
    """
    currencies_df: pl.DataFrame = pl.read_csv(
        Path(__file__).parent / "data" / "currencies.csv"
    )

    with session_maker.begin() as session:
        for row in currencies_df.rows(named=True):
            currency: Currency | None = session.get(entity=Currency, ident=row["id"])
            if currency:
                continue

            currency = Currency(**row)
            session.add(instance=currency)
