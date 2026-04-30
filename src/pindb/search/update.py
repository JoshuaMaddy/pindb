"""Meilisearch index lifecycle: settings, bulk sync from Postgres, add/delete helpers."""

from __future__ import annotations

import logging
from typing import Iterable, Protocol, Sequence

from meilisearch_python_sdk import AsyncIndex
from meilisearch_python_sdk.errors import MeilisearchApiError
from meilisearch_python_sdk.models.settings import FilterableAttributes
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from pindb.config import CONFIGURATION
from pindb.database import async_session_maker
from pindb.database.artist import Artist
from pindb.database.entity_type import EntityType
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.database.tag import Tag

LOGGER: logging.Logger = logging.getLogger(name="pindb.search.update")


def _pin_index() -> AsyncIndex:
    return CONFIGURATION.meili_client.index(uid=CONFIGURATION.meilisearch_index)


def _tags_index() -> AsyncIndex:
    return CONFIGURATION.meili_client.index(uid="tags")


def _artists_index() -> AsyncIndex:
    return CONFIGURATION.meili_client.index(uid="artists")


def _shops_index() -> AsyncIndex:
    return CONFIGURATION.meili_client.index(uid="shops")


def _pin_sets_index() -> AsyncIndex:
    return CONFIGURATION.meili_client.index(uid="pin_sets")


INDEX_BY_ENTITY_TYPE: dict[EntityType, AsyncIndex] = {
    EntityType.pin: _pin_index(),
    EntityType.tag: _tags_index(),
    EntityType.artist: _artists_index(),
    EntityType.shop: _shops_index(),
    EntityType.pin_set: _pin_sets_index(),
}


class _Indexable(Protocol):
    id: int

    def document(self) -> dict[str, object]: ...


# ---------------------------------------------------------------------------
# Index bootstrap
# ---------------------------------------------------------------------------


async def _create_index(
    uid: str, searchable: list[str], filterable: Sequence[str] | None = None
) -> AsyncIndex:
    client = CONFIGURATION.meili_client
    index = await client.get_or_create_index(uid, primary_key="id")
    await index.update_searchable_attributes(searchable)
    if filterable:
        filterable_attributes: list[str | FilterableAttributes] = list(filterable)
        await index.update_filterable_attributes(filterable_attributes)
    return index


async def setup_index() -> None:
    """Create indexes if needed and apply searchable/filterable attribute settings."""
    LOGGER.info("Configuring Meilisearch indexes.")
    await _create_index(
        uid=CONFIGURATION.meilisearch_index,
        searchable=[
            "name",
            "tags",
            "artists",
            "shops",
            "tag_aliases",
            "artist_aliases",
            "shop_aliases",
            "description",
        ],
    )
    await _create_index(
        uid="tags",
        searchable=["display_name", "name", "aliases", "category"],
        filterable=["category"],
    )
    await _create_index(uid="artists", searchable=["name", "aliases", "description"])
    await _create_index(uid="shops", searchable=["name", "aliases", "description"])
    await _create_index(uid="pin_sets", searchable=["name", "description"])


# ---------------------------------------------------------------------------
# Generic CRUD keyed off EntityType
# ---------------------------------------------------------------------------


async def update_one(entity_type: EntityType, entity: _Indexable) -> None:
    index = INDEX_BY_ENTITY_TYPE[entity_type]
    await index.add_documents(documents=[entity.document()])


async def update_many(entity_type: EntityType, entities: Iterable[_Indexable]) -> None:
    documents = [entity.document() for entity in entities]
    LOGGER.info("Updating %s %s documents", len(documents), entity_type.slug)
    index = INDEX_BY_ENTITY_TYPE[entity_type]
    await index.add_documents(documents=documents)


async def delete_one(entity_type: EntityType, entity_id: int) -> None:
    LOGGER.info("Deleting %s ID %s from index.", entity_type.slug, entity_id)
    index = INDEX_BY_ENTITY_TYPE[entity_type]
    await index.delete_document(str(entity_id))


# ---------------------------------------------------------------------------
# Thin entity-specific wrappers — keep existing call sites working
# ---------------------------------------------------------------------------


async def update_pin(pin: Pin) -> None:
    LOGGER.info("Updating Pin with ID: %s", pin.id)
    await update_one(EntityType.pin, pin)


async def update_pins(pins: Iterable[Pin]) -> None:
    await update_many(EntityType.pin, pins)


async def delete_pin(pin_id: int) -> None:
    await delete_one(EntityType.pin, pin_id)


async def update_tag(tag: Tag) -> None:
    await update_one(EntityType.tag, tag)


async def update_tags(tags: Iterable[Tag]) -> None:
    await update_many(EntityType.tag, tags)


async def delete_tag(tag_id: int) -> None:
    await delete_one(EntityType.tag, tag_id)


async def update_artist(artist: Artist) -> None:
    await update_one(EntityType.artist, artist)


async def update_artists(artists: Iterable[Artist]) -> None:
    await update_many(EntityType.artist, artists)


async def delete_artist(artist_id: int) -> None:
    await delete_one(EntityType.artist, artist_id)


async def update_shop(shop: Shop) -> None:
    await update_one(EntityType.shop, shop)


async def update_shops(shops: Iterable[Shop]) -> None:
    await update_many(EntityType.shop, shops)


async def delete_shop(shop_id: int) -> None:
    await delete_one(EntityType.shop, shop_id)


async def update_pin_set(pin_set: PinSet) -> None:
    await update_one(EntityType.pin_set, pin_set)


async def update_pin_sets(pin_sets: Iterable[PinSet]) -> None:
    await update_many(EntityType.pin_set, pin_sets)


async def delete_pin_set(pin_set_id: int) -> None:
    await delete_one(EntityType.pin_set, pin_set_id)


# ---------------------------------------------------------------------------
# Full-index sync
# ---------------------------------------------------------------------------


async def _get_all_meili_ids(index: AsyncIndex) -> set[int]:
    ids: set[int] = set()
    limit = 1000
    offset = 0
    while True:
        try:
            result = await index.get_documents(
                fields=["id"],
                limit=limit,
                offset=offset,
            )
        except MeilisearchApiError as error:
            if error.code and "index_not_found" in str(error.code).lower():
                return ids
            raise
        for document in result.results:
            raw = document.get("id")
            if raw is not None:
                ids.add(int(raw))
        if offset + limit >= result.total:
            break
        offset += limit
    return ids


async def _sync_index(index: AsyncIndex, entities: Sequence[_Indexable]) -> None:
    db_ids: set[int] = {entity.id for entity in entities}
    if entities:
        await index.add_documents([entity.document() for entity in entities])
    meili_ids: set[int] = await _get_all_meili_ids(index)
    stale: list[str] = [str(i) for i in (meili_ids - db_ids)]
    if stale:
        LOGGER.info("Deleting %s stale docs from %s.", len(stale), index.uid)
        await index.delete_documents(stale)


async def _fetch_all(
    session: AsyncSession,
) -> tuple[
    Sequence[Pin],
    Sequence[Tag],
    Sequence[Artist],
    Sequence[Shop],
    Sequence[PinSet],
]:
    pin_result = await session.scalars(
        select(Pin).options(
            selectinload(Pin.shops).selectinload(Shop.aliases),
            selectinload(Pin.tags).selectinload(Tag.aliases),
            selectinload(Pin.artists).selectinload(Artist.aliases),
        )
    )
    return (
        pin_result.all(),
        (await session.scalars(select(Tag).options(selectinload(Tag.aliases)))).all(),
        (
            await session.scalars(select(Artist).options(selectinload(Artist.aliases)))
        ).all(),
        (await session.scalars(select(Shop).options(selectinload(Shop.aliases)))).all(),
        (await session.scalars(select(PinSet))).all(),
    )


async def _fetch_entity_for_sync(
    session: AsyncSession, entity_type: EntityType, entity_id: int
) -> _Indexable | None:
    if entity_type == EntityType.pin:
        return await session.scalar(
            select(Pin)
            .where(Pin.id == entity_id)
            .options(
                selectinload(Pin.shops).selectinload(Shop.aliases),
                selectinload(Pin.tags).selectinload(Tag.aliases),
                selectinload(Pin.artists).selectinload(Artist.aliases),
            )
        )
    if entity_type == EntityType.tag:
        return await session.scalar(
            select(Tag).where(Tag.id == entity_id).options(selectinload(Tag.aliases))
        )
    if entity_type == EntityType.artist:
        return await session.scalar(
            select(Artist)
            .where(Artist.id == entity_id)
            .options(selectinload(Artist.aliases))
        )
    if entity_type == EntityType.shop:
        return await session.scalar(
            select(Shop).where(Shop.id == entity_id).options(selectinload(Shop.aliases))
        )
    if entity_type == EntityType.pin_set:
        return await session.get(PinSet, entity_id)
    return None


async def sync_entity(entity_type: EntityType, entity_id: int) -> None:
    """Re-fetch entity from DB and upsert to Meili, or delete if absent/deleted."""
    async with async_session_maker() as session:
        entity = await _fetch_entity_for_sync(session, entity_type, entity_id)
    if entity is None:
        await delete_one(entity_type, entity_id)
    else:
        await update_one(entity_type, entity)


async def sync_pin_with_deps(pin_id: int) -> None:
    """Sync pin and its related shops/artists/tags after cascade approval."""
    async with async_session_maker() as session:
        pin = await session.scalar(
            select(Pin)
            .where(Pin.id == pin_id)
            .options(
                selectinload(Pin.shops).selectinload(Shop.aliases),
                selectinload(Pin.tags).selectinload(Tag.aliases),
                selectinload(Pin.artists).selectinload(Artist.aliases),
            )
        )
    if pin is None:
        await delete_one(EntityType.pin, pin_id)
        return
    await update_pin(pin)
    for shop in pin.shops:
        await update_shop(shop)
    for tag in pin.tags:
        await update_tag(tag)
    for artist in pin.artists:
        await update_artist(artist)


async def update_all() -> None:
    """Reconcile every Meilisearch index with the current database rows (add + prune)."""
    LOGGER.info("Updating all search indexes.")
    async with async_session_maker() as session:
        pins, tags, artists, shops, pin_sets = await _fetch_all(session)

    # Refresh dict entries so AsyncIndex uses current client
    await _sync_index(_pin_index(), pins)
    await _sync_index(_tags_index(), tags)
    await _sync_index(_artists_index(), artists)
    await _sync_index(_shops_index(), shops)
    await _sync_index(_pin_sets_index(), pin_sets)
