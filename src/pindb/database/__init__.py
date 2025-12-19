from pathlib import Path

import polars as pl
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker as SessionMaker

from pindb.config import CONFIGURATION
from pindb.database.artist import Artist
from pindb.database.base import Base
from pindb.database.currency import Currency
from pindb.database.link import Link
from pindb.database.material import Material
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.database.tag import Tag

__all__ = [
    "Artist",
    "Base",
    "Currency",
    "Link",
    "Material",
    "Pin",
    "PinSet",
    "Shop",
    "Tag",
]

# Create engine, database
__engine = create_engine(CONFIGURATION.database_connection)
Base.metadata.create_all(__engine)

# Expose sessionmaker
session_maker = SessionMaker(bind=__engine)

# Create/update currencies table
__currencies_df = pl.read_csv(Path(__file__).parent / "data" / "currencies.csv")

with session_maker.begin() as session:
    for row in __currencies_df.rows(named=True):
        currency = session.get(Currency, row["id"])
        if currency:
            continue

        currency = Currency(**row)
        session.add(currency)
