from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker as SessionMaker

from pindb.config import CONFIGURATION
from pindb.database.artist import Artist
from pindb.database.base import Base
from pindb.database.link import Link
from pindb.database.material import Material
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.database.tag import Tag

__all__ = [
    "Artist",
    "Base",
    "Link",
    "Material",
    "Pin",
    "PinSet",
    "Shop",
    "Tag",
]

engine = create_engine(CONFIGURATION.database_connection)
Base.metadata.create_all(engine)

session_maker = SessionMaker(bind=engine)
