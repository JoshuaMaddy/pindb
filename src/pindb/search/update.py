import logging
from typing import Iterable, Sequence

from meilisearch.index import Index
from meilisearch.models.document import DocumentsResults
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from pindb.config import CONFIGURATION
from pindb.database import session_maker
from pindb.database.artist import Artist
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.database.tag import Tag

LOGGER: logging.Logger = logging.getLogger(name="pindb.search.update")

PIN_INDEX: Index = CONFIGURATION.meili_client.index(uid=CONFIGURATION.meilisearch_index)
TAGS_INDEX: Index = CONFIGURATION.meili_client.index(uid="tags")
ARTISTS_INDEX: Index = CONFIGURATION.meili_client.index(uid="artists")
SHOPS_INDEX: Index = CONFIGURATION.meili_client.index(uid="shops")
PIN_SETS_INDEX: Index = CONFIGURATION.meili_client.index(uid="pin_sets")


def _create_index(
    uid: str, searchable: list[str], filterable: list[str] | None = None
) -> Index:
    index: Index = CONFIGURATION.meili_client.index(uid=uid)
    try:
        CONFIGURATION.meili_client.create_index(uid=uid, options={"primaryKey": "id"})
    except Exception:
        pass
    index.update_searchable_attributes(searchable)
    if filterable:
        index.update_filterable_attributes(filterable)
    return index


def setup_index() -> None:
    LOGGER.info("Configuring Meilisearch indexes.")
    _create_index(
        uid=CONFIGURATION.meilisearch_index,
        searchable=["name", "tags", "artists", "shops", "description"],
    )
    _create_index(
        uid="tags", searchable=["name", "aliases", "category"], filterable=["category"]
    )
    _create_index(uid="artists", searchable=["name", "description"])
    _create_index(uid="shops", searchable=["name", "description"])
    _create_index(uid="pin_sets", searchable=["name", "description"])


# --- Pins ---


def update_pin(pin: Pin) -> None:
    LOGGER.info(msg=f"Updating Pin with ID: {pin.id}")
    PIN_INDEX.add_documents(documents=[pin.document()])


def update_pins(pins: Iterable[Pin]) -> None:
    docs = [pin.document() for pin in pins]
    LOGGER.info(msg=f"Updating {len(docs)} pins")
    PIN_INDEX.add_documents(documents=docs)


def delete_pin(pin_id: int) -> None:
    LOGGER.info(f"Deleting Pin ID {pin_id} from index.")
    PIN_INDEX.delete_document(pin_id)


# --- Tags ---


def update_tag(tag: Tag) -> None:
    TAGS_INDEX.add_documents(documents=[tag.document()])


def update_tags(tags: Iterable[Tag]) -> None:
    TAGS_INDEX.add_documents(documents=[t.document() for t in tags])


def delete_tag(tag_id: int) -> None:
    TAGS_INDEX.delete_document(tag_id)


# --- Artists ---


def update_artist(artist: Artist) -> None:
    ARTISTS_INDEX.add_documents(documents=[artist.document()])


def update_artists(artists: Iterable[Artist]) -> None:
    ARTISTS_INDEX.add_documents(documents=[a.document() for a in artists])


def delete_artist(artist_id: int) -> None:
    ARTISTS_INDEX.delete_document(artist_id)


# --- Shops ---


def update_shop(shop: Shop) -> None:
    SHOPS_INDEX.add_documents(documents=[shop.document()])


def update_shops(shops: Iterable[Shop]) -> None:
    SHOPS_INDEX.add_documents(documents=[s.document() for s in shops])


def delete_shop(shop_id: int) -> None:
    SHOPS_INDEX.delete_document(shop_id)


# --- PinSets ---


def update_pin_set(pin_set: PinSet) -> None:
    PIN_SETS_INDEX.add_documents(documents=[pin_set.document()])


def update_pin_sets(pin_sets: Iterable[PinSet]) -> None:
    PIN_SETS_INDEX.add_documents(documents=[ps.document() for ps in pin_sets])


def delete_pin_set(pin_set_id: int) -> None:
    PIN_SETS_INDEX.delete_document(pin_set_id)


# --- Sync helpers ---


def _get_all_meili_ids(index: Index) -> set[int]:
    from meilisearch.errors import MeilisearchApiError

    ids: set[int] = set()
    limit = 1000
    offset = 0
    while True:
        try:
            result: DocumentsResults = index.get_documents(
                {"fields": ["id"], "limit": limit, "offset": offset}
            )
        except MeilisearchApiError as e:
            if e.code == "index_not_found":
                return ids
            raise
        for doc in result.results:
            ids.add(getattr(doc, "id"))
        if offset + limit >= result.total:
            break
        offset += limit
    return ids


def _sync_index(index: Index, entities: Sequence[object]) -> None:
    db_ids: set[int] = {getattr(e, "id") for e in entities}
    if entities:
        index.add_documents([getattr(e, "document")() for e in entities])
    meili_ids: set[int] = _get_all_meili_ids(index)
    stale: list[int] = list(meili_ids - db_ids)
    if stale:
        LOGGER.info(f"Deleting {len(stale)} stale docs from {index.uid}.")
        index.delete_documents(stale)


def _fetch_all(
    session: Session,
) -> tuple[
    Sequence[Pin],
    Sequence[Tag],
    Sequence[Artist],
    Sequence[Shop],
    Sequence[PinSet],
]:
    return (
        session.scalars(
            select(Pin).options(
                selectinload(Pin.shops),
                selectinload(Pin.tags),
                selectinload(Pin.artists),
            )
        ).all(),
        session.scalars(select(Tag).options(selectinload(Tag.aliases))).all(),
        session.scalars(select(Artist)).all(),
        session.scalars(select(Shop)).all(),
        session.scalars(select(PinSet)).all(),
    )


def update_all() -> None:
    LOGGER.info(msg="Updating all search indexes.")
    with session_maker() as session:
        pins, tags, artists, shops, pin_sets = _fetch_all(session)

    _sync_index(PIN_INDEX, pins)
    _sync_index(TAGS_INDEX, tags)
    _sync_index(ARTISTS_INDEX, artists)
    _sync_index(SHOPS_INDEX, shops)
    _sync_index(PIN_SETS_INDEX, pin_sets)
