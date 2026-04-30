"""Meilisearch query helpers and Pydantic wrappers for API responses."""

from __future__ import annotations

import re

from meilisearch_python_sdk import AsyncIndex
from meilisearch_python_sdk.models.search import SearchResults
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from pindb.config import CONFIGURATION
from pindb.database.artist import Artist
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.database.tag import Tag, TagCategory

PIN_INDEX: AsyncIndex = CONFIGURATION.meili_client.index(
    uid=CONFIGURATION.meilisearch_index
)
TAGS_INDEX: AsyncIndex = CONFIGURATION.meili_client.index(uid="tags")
ARTISTS_INDEX: AsyncIndex = CONFIGURATION.meili_client.index(uid="artists")
SHOPS_INDEX: AsyncIndex = CONFIGURATION.meili_client.index(uid="shops")
PIN_SETS_INDEX: AsyncIndex = CONFIGURATION.meili_client.index(uid="pin_sets")


def meilisearch_hit_dicts(raw: dict[str, object]) -> list[dict[str, object]]:
    """Return the ``hits`` array from a Meilisearch search response as typed dict rows."""
    hits_value = raw.get("hits", [])
    if not isinstance(hits_value, list):
        return []
    rows: list[dict[str, object]] = []
    for element in hits_value:
        if isinstance(element, dict):
            rows.append({str(key): value for key, value in element.items()})
    return rows


def meilisearch_total_hits(raw: dict[str, object], *, hit_count: int) -> int:
    """Best-effort total from Meilisearch response keys, falling back to ``hit_count``."""
    estimated = raw.get("estimatedTotalHits", raw.get("estimated_total_hits"))
    if isinstance(estimated, int):
        return estimated
    total_hits_value = raw.get("totalHits", raw.get("total_hits"))
    if isinstance(total_hits_value, int):
        return total_hits_value
    return hit_count


def _hit_ids_from_documents(hits: list[dict[str, object]]) -> list[int]:
    ids: list[int] = []
    for hit in hits:
        raw_id = hit["id"]
        if isinstance(raw_id, int) and not isinstance(raw_id, bool):
            ids.append(raw_id)
        elif isinstance(raw_id, str):
            ids.append(int(raw_id))
        else:
            msg = f"Meilisearch hit id must be int or str, got {type(raw_id)}"
            raise TypeError(
                msg,
            )
    return ids


def _search_results_to_raw(sr: SearchResults | object) -> dict[str, object]:
    if isinstance(sr, dict):
        return {str(k): v for k, v in sr.items()}
    dump = (
        sr.model_dump(mode="python", by_alias=True)
        if isinstance(sr, SearchResults)
        else {}
    )
    return {str(k): v for k, v in dump.items()}


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

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_raw(cls, raw: dict[str, object]) -> "PinSearchResult":

        def to_snake(s: str) -> str:
            return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", s).lower()

        normalized: dict[str, object] = {to_snake(k): v for k, v in raw.items()}
        return cls.model_validate(normalized)


async def search_pin(query: str, session: AsyncSession) -> list[Pin] | None:
    """Search pins in Meilisearch and hydrate ORM rows in hit order (with shops/artists)."""
    search_results: SearchResults = await PIN_INDEX.search(query=query)  # type: ignore[assignment]
    raw = _search_results_to_raw(search_results)
    result = PinSearchResult.from_raw(raw)

    if not result.hits:
        return None

    pin_ids: list[int] = [hit.id for hit in result.hits]

    rows = (
        await session.scalars(
            select(Pin)
            .where(Pin.id.in_(pin_ids))
            .options(selectinload(Pin.shops), selectinload(Pin.artists))
        )
    ).all()
    pins_by_id: dict[int, Pin] = {pin.id: pin for pin in rows}
    return [pins_by_id[pid] for pid in pin_ids if pid in pins_by_id]


async def _search_index(
    index: AsyncIndex,
    query: str,
    offset: int = 0,
    limit: int = 100,
    filter_str: str | None = None,
) -> tuple[list[int], int]:
    """Return (ids in meili result order, estimated_total_hits)."""
    if filter_str is not None:
        raw_sr = await index.search(
            query, offset=offset, limit=limit, filter=filter_str
        )
    else:
        raw_sr = await index.search(query, offset=offset, limit=limit)
    raw = _search_results_to_raw(raw_sr)
    hits = meilisearch_hit_dicts(raw)
    total = meilisearch_total_hits(raw, hit_count=len(hits))
    ids = _hit_ids_from_documents(hits)
    return ids, total


async def search_tags(
    query: str,
    session: AsyncSession,
    category: TagCategory | None = None,
    offset: int = 0,
    limit: int = 100,
) -> tuple[list[Tag], int]:
    filter_str: str | None = f'category = "{category.value}"' if category else None
    ids, total = await _search_index(TAGS_INDEX, query, offset, limit, filter_str)
    if not ids:
        return [], total
    rows = (
        await session.scalars(
            select(Tag).where(Tag.id.in_(ids)).options(selectinload(Tag.pins))
        )
    ).all()
    tags_by_id: dict[int, Tag] = {t.id: t for t in rows}
    return [tags_by_id[i] for i in ids if i in tags_by_id], total


async def search_artists(
    query: str,
    session: AsyncSession,
    offset: int = 0,
    limit: int = 100,
) -> tuple[list[Artist], int]:
    ids, total = await _search_index(ARTISTS_INDEX, query, offset, limit)
    if not ids:
        return [], total
    rows = (
        await session.scalars(
            select(Artist).where(Artist.id.in_(ids)).options(selectinload(Artist.pins))
        )
    ).all()
    artists_by_id: dict[int, Artist] = {a.id: a for a in rows}
    return [artists_by_id[i] for i in ids if i in artists_by_id], total


async def search_shops(
    query: str,
    session: AsyncSession,
    offset: int = 0,
    limit: int = 100,
) -> tuple[list[Shop], int]:
    ids, total = await _search_index(SHOPS_INDEX, query, offset, limit)
    if not ids:
        return [], total
    rows = (
        await session.scalars(
            select(Shop).where(Shop.id.in_(ids)).options(selectinload(Shop.pins))
        )
    ).all()
    shops_by_id: dict[int, Shop] = {s.id: s for s in rows}
    return [shops_by_id[i] for i in ids if i in shops_by_id], total


async def search_pin_sets(
    query: str,
    session: AsyncSession,
    offset: int = 0,
    limit: int = 100,
) -> tuple[list[PinSet], int]:
    ids, total = await _search_index(PIN_SETS_INDEX, query, offset, limit)
    if not ids:
        return [], total
    rows = (
        await session.scalars(
            select(PinSet).where(PinSet.id.in_(ids)).options(selectinload(PinSet.pins))
        )
    ).all()
    pin_sets_by_id: dict[int, PinSet] = {ps.id: ps for ps in rows}
    return [pin_sets_by_id[i] for i in ids if i in pin_sets_by_id], total


async def search_entity_options(
    index: AsyncIndex,
    query: str,
    limit: int = 50,
) -> list[dict[str, str]]:
    """Search an entity index and return Tom Select option dicts.

    Hits come directly from meili (no DB roundtrip). is_pending is stored
    in the document so the (P) prefix can be applied without a DB query.
    """
    raw_sr = await index.search(query, limit=limit)  # type: ignore[call-arg]
    raw = _search_results_to_raw(raw_sr)
    hits = meilisearch_hit_dicts(raw)
    results: list[dict[str, str]] = []
    for hit in hits:
        text = str(hit.get("display_name") or hit["name"])
        item: dict[str, str] = {
            "value": str(hit["id"]),
            "text": ("(P) " + text) if hit.get("is_pending") else text,
        }
        if "category" in hit:
            item["category"] = str(hit["category"])
        if "front_image_guid" in hit:
            item["thumbnail"] = f"/get/image/{hit['front_image_guid']}?w=100"
        results.append(item)
    return results
