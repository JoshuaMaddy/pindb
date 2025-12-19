from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from pindb.config import CONFIGURATION
from pindb.database.pin import Pin

PIN_INDEX = CONFIGURATION.meili_client.index(uid=CONFIGURATION.meilisearch_index)


def search_pin(query: str, session: Session) -> Sequence[Pin] | None:
    result: dict[str, Any] = PIN_INDEX.search(query=query)
    hits: Any | None = result.get("hits")

    if not hits:
        return None

    pin_ids: list[int] = [hit.get("id") for hit in hits if hit.get("id")]

    return session.scalars(statement=select(Pin).where(Pin.id.in_(other=pin_ids))).all()
