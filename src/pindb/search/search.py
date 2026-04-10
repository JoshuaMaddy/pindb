from meilisearch.index import Index
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from pindb.config import CONFIGURATION
from pindb.database.pin import Pin

PIN_INDEX: Index = CONFIGURATION.meili_client.index(uid=CONFIGURATION.meilisearch_index)


class PinSearchHit(BaseModel):
    id: int
    name: str
    shops: list[str]
    materials: list[str]
    tags: list[str] = []
    artists: list[str] = []
    description: str | None = None


class PinSearchResult(BaseModel):
    hits: list[PinSearchHit]
    offset: int
    limit: int
    estimated_total_hits: int | None = None
    total_hits: int | None = None
    total_pages: int | None = None
    hits_per_page: int | None = None
    page: int | None = None
    processing_time_ms: int
    query: str

    model_config: dict[str, bool | None] = {
        "populate_by_name": True,
        "alias_generator": None,
    }

    @classmethod
    def from_raw(cls, raw: dict[str, object]) -> "PinSearchResult":
        import re

        # Meilisearch returns camelCase keys; convert to snake_case for Pydantic
        def to_snake(s: str) -> str:
            return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", s).lower()

        normalized: dict[str, object] = {to_snake(k): v for k, v in raw.items()}
        return cls.model_validate(normalized)


def search_pin(query: str, session: Session) -> list[Pin] | None:
    raw: dict[str, object] = PIN_INDEX.search(query=query)  # type: ignore[assignment]
    result: PinSearchResult = PinSearchResult.from_raw(raw)

    if not result.hits:
        return None

    pin_ids: list[int] = [hit.id for hit in result.hits]

    pins_by_id: dict[int, Pin] = {
        pin.id: pin
        for pin in session.scalars(
            statement=select(Pin)
            .where(Pin.id.in_(other=pin_ids))
            .options(selectinload(Pin.shops), selectinload(Pin.artists))
        ).all()
    }
    return [pins_by_id[pid] for pid in pin_ids if pid in pins_by_id]
