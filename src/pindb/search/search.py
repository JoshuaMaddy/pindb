from meilisearch.index import Index
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from pindb.config import CONFIGURATION
from pindb.database.artist import Artist
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.database.tag import Tag, TagCategory

PIN_INDEX: Index = CONFIGURATION.meili_client.index(uid=CONFIGURATION.meilisearch_index)
TAGS_INDEX: Index = CONFIGURATION.meili_client.index(uid="tags")
ARTISTS_INDEX: Index = CONFIGURATION.meili_client.index(uid="artists")
SHOPS_INDEX: Index = CONFIGURATION.meili_client.index(uid="shops")
PIN_SETS_INDEX: Index = CONFIGURATION.meili_client.index(uid="pin_sets")


class PinSearchHit(BaseModel):
    id: int
    name: str
    shops: list[str]
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


def _search_index(
    index: Index,
    query: str,
    offset: int = 0,
    limit: int = 100,
    filter_str: str | None = None,
) -> tuple[list[int], int]:
    """Return (ids in meili result order, estimated_total_hits)."""
    opt_params: dict[str, object] = {"offset": offset, "limit": limit}
    if filter_str:
        opt_params["filter"] = filter_str
    raw: dict[str, object] = index.search(query=query, opt_params=opt_params)  # type: ignore[assignment]
    hits: list[dict[str, object]] = raw.get("hits", [])  # type: ignore[assignment]
    total: int = int(raw.get("estimatedTotalHits") or raw.get("totalHits") or len(hits))
    ids: list[int] = [int(h["id"]) for h in hits]
    return ids, total


def search_tags(
    query: str,
    session: Session,
    category: TagCategory | None = None,
    offset: int = 0,
    limit: int = 100,
) -> tuple[list[Tag], int]:
    filter_str: str | None = f'category = "{category.value}"' if category else None
    ids, total = _search_index(TAGS_INDEX, query, offset, limit, filter_str)
    if not ids:
        return [], total
    tags_by_id: dict[int, Tag] = {
        t.id: t
        for t in session.scalars(
            select(Tag).where(Tag.id.in_(ids)).options(selectinload(Tag.pins))
        ).all()
    }
    return [tags_by_id[i] for i in ids if i in tags_by_id], total


def search_artists(
    query: str,
    session: Session,
    offset: int = 0,
    limit: int = 100,
) -> tuple[list[Artist], int]:
    ids, total = _search_index(ARTISTS_INDEX, query, offset, limit)
    if not ids:
        return [], total
    artists_by_id: dict[int, Artist] = {
        a.id: a
        for a in session.scalars(
            select(Artist).where(Artist.id.in_(ids)).options(selectinload(Artist.pins))
        ).all()
    }
    return [artists_by_id[i] for i in ids if i in artists_by_id], total


def search_shops(
    query: str,
    session: Session,
    offset: int = 0,
    limit: int = 100,
) -> tuple[list[Shop], int]:
    ids, total = _search_index(SHOPS_INDEX, query, offset, limit)
    if not ids:
        return [], total
    shops_by_id: dict[int, Shop] = {
        s.id: s
        for s in session.scalars(
            select(Shop).where(Shop.id.in_(ids)).options(selectinload(Shop.pins))
        ).all()
    }
    return [shops_by_id[i] for i in ids if i in shops_by_id], total


def search_pin_sets(
    query: str,
    session: Session,
    offset: int = 0,
    limit: int = 100,
) -> tuple[list[PinSet], int]:
    ids, total = _search_index(PIN_SETS_INDEX, query, offset, limit)
    if not ids:
        return [], total
    pin_sets_by_id: dict[int, PinSet] = {
        ps.id: ps
        for ps in session.scalars(
            select(PinSet).where(PinSet.id.in_(ids)).options(selectinload(PinSet.pins))
        ).all()
    }
    return [pin_sets_by_id[i] for i in ids if i in pin_sets_by_id], total


def search_entity_options(
    index: Index,
    query: str,
    limit: int = 50,
) -> list[dict[str, str]]:
    """Search an entity index and return Tom Select option dicts.

    Hits come directly from meili (no DB roundtrip). is_pending is stored
    in the document so the (P) prefix can be applied without a DB query.
    """
    raw: dict[str, object] = index.search(query=query, opt_params={"limit": limit})  # type: ignore[assignment]
    hits: list[dict[str, object]] = raw.get("hits", [])  # type: ignore[assignment]
    results = []
    for hit in hits:
        text = str(hit.get("display_name") or hit["name"])
        item: dict[str, str] = {
            "value": str(hit["id"]),
            "text": ("(P) " + text) if hit.get("is_pending") else text,
        }
        if "category" in hit:
            item["category"] = str(hit["category"])
        results.append(item)
    return results
