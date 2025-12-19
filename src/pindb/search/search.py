from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from pindb.config import CONFIGURATION
from pindb.database.pin import Pin

PIN_INDEX = CONFIGURATION.meili_client.index(CONFIGURATION.meilisearch_index)


def search_pin(query: str, session: Session) -> Sequence[Pin] | None:
    result = PIN_INDEX.search(query=query)
    hits = result.get("hits")

    if not hits:
        return None

    pin_ids: list[int] = [hit.get("id") for hit in hits if hit.get("id")]

    return session.scalars(select(Pin).where(Pin.id.in_(pin_ids))).all()
