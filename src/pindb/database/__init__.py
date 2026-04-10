from pathlib import Path

import polars as pl
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker as SessionMaker
from sqlalchemy.orm.session import Session, sessionmaker

from pindb.config import CONFIGURATION
from pindb.database.artist import Artist
from pindb.database.base import Base
from pindb.database.currency import Currency
from pindb.database.grade import Grade
from pindb.database.link import Link
from pindb.database.material import Material
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.session import UserSession
from pindb.database.shop import Shop
from pindb.database.tag import Tag
from pindb.database.user import User
from pindb.database.user_auth_provider import UserAuthProvider

__all__: list[str] = [
    "seed_currencies",
    "Artist",
    "Base",
    "Currency",
    "Grade",
    "Link",
    "Material",
    "Pin",
    "PinSet",
    "Shop",
    "Tag",
    "User",
    "UserAuthProvider",
    "UserSession",
]

# Create engine
__engine: Engine = create_engine(CONFIGURATION.database_connection)

# Expose sessionmaker
session_maker: sessionmaker[Session] = SessionMaker(
    bind=__engine, expire_on_commit=False
)


def seed_currencies() -> None:
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
