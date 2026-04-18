import logging
from typing import Iterable, Protocol, Sequence

from meilisearch.index import Index
from meilisearch.models.document import DocumentsResults
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from pindb.config import CONFIGURATION
from pindb.database import session_maker
from pindb.database.artist import Artist
from pindb.database.entity_type import EntityType
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


INDEX_BY_ENTITY_TYPE: dict[EntityType, Index] = {
    EntityType.pin: PIN_INDEX,
    EntityType.tag: TAGS_INDEX,
    EntityType.artist: ARTISTS_INDEX,
    EntityType.shop: SHOPS_INDEX,
    EntityType.pin_set: PIN_SETS_INDEX,
}


class _Indexable(Protocol):
    id: int

    def document(self) -> dict[str, object]: ...


# ---------------------------------------------------------------------------
# Index bootstrap
# ---------------------------------------------------------------------------


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
        uid="tags",
        searchable=["display_name", "name", "aliases", "category"],
        filterable=["category"],
    )
    _create_index(uid="artists", searchable=["name", "aliases", "description"])
    _create_index(uid="shops", searchable=["name", "aliases", "description"])
    _create_index(uid="pin_sets", searchable=["name", "description"])


# ---------------------------------------------------------------------------
# Generic CRUD keyed off EntityType
# ---------------------------------------------------------------------------


def update_one(entity_type: EntityType, entity: _Indexable) -> None:
    INDEX_BY_ENTITY_TYPE[entity_type].add_documents(documents=[entity.document()])


def update_many(entity_type: EntityType, entities: Iterable[_Indexable]) -> None:
    documents = [entity.document() for entity in entities]
    LOGGER.info(f"Updating {len(documents)} {entity_type.slug} documents")
    INDEX_BY_ENTITY_TYPE[entity_type].add_documents(documents=documents)


def delete_one(entity_type: EntityType, entity_id: int) -> None:
    LOGGER.info(f"Deleting {entity_type.slug} ID {entity_id} from index.")
    INDEX_BY_ENTITY_TYPE[entity_type].delete_document(entity_id)


# ---------------------------------------------------------------------------
# Thin entity-specific wrappers — keep existing call sites working
# ---------------------------------------------------------------------------


def update_pin(pin: Pin) -> None:
    LOGGER.info(f"Updating Pin with ID: {pin.id}")
    update_one(EntityType.pin, pin)


def update_pins(pins: Iterable[Pin]) -> None:
    update_many(EntityType.pin, pins)


def delete_pin(pin_id: int) -> None:
    delete_one(EntityType.pin, pin_id)


def update_tag(tag: Tag) -> None:
    update_one(EntityType.tag, tag)


def update_tags(tags: Iterable[Tag]) -> None:
    update_many(EntityType.tag, tags)


def delete_tag(tag_id: int) -> None:
    delete_one(EntityType.tag, tag_id)


def update_artist(artist: Artist) -> None:
    update_one(EntityType.artist, artist)


def update_artists(artists: Iterable[Artist]) -> None:
    update_many(EntityType.artist, artists)


def delete_artist(artist_id: int) -> None:
    delete_one(EntityType.artist, artist_id)


def update_shop(shop: Shop) -> None:
    update_one(EntityType.shop, shop)


def update_shops(shops: Iterable[Shop]) -> None:
    update_many(EntityType.shop, shops)


def delete_shop(shop_id: int) -> None:
    delete_one(EntityType.shop, shop_id)


def update_pin_set(pin_set: PinSet) -> None:
    update_one(EntityType.pin_set, pin_set)


def update_pin_sets(pin_sets: Iterable[PinSet]) -> None:
    update_many(EntityType.pin_set, pin_sets)


def delete_pin_set(pin_set_id: int) -> None:
    delete_one(EntityType.pin_set, pin_set_id)


# ---------------------------------------------------------------------------
# Full-index sync
# ---------------------------------------------------------------------------


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
        except MeilisearchApiError as error:
            if error.code == "index_not_found":
                return ids
            raise
        for document in result.results:
            ids.add(getattr(document, "id"))
        if offset + limit >= result.total:
            break
        offset += limit
    return ids


def _sync_index(index: Index, entities: Sequence[_Indexable]) -> None:
    db_ids: set[int] = {entity.id for entity in entities}
    if entities:
        index.add_documents([entity.document() for entity in entities])
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
                selectinload(Pin.shops).selectinload(Shop.aliases),
                selectinload(Pin.tags),
                selectinload(Pin.artists).selectinload(Artist.aliases),
            )
        ).all(),
        session.scalars(select(Tag).options(selectinload(Tag.aliases))).all(),
        session.scalars(select(Artist).options(selectinload(Artist.aliases))).all(),
        session.scalars(select(Shop).options(selectinload(Shop.aliases))).all(),
        session.scalars(select(PinSet)).all(),
    )


def update_all() -> None:
    LOGGER.info("Updating all search indexes.")
    with session_maker() as session:
        pins, tags, artists, shops, pin_sets = _fetch_all(session)

    _sync_index(PIN_INDEX, pins)
    _sync_index(TAGS_INDEX, tags)
    _sync_index(ARTISTS_INDEX, artists)
    _sync_index(SHOPS_INDEX, shops)
    _sync_index(PIN_SETS_INDEX, pin_sets)
