import logging
from typing import Iterable, Sequence

from meilisearch.index import Index
from meilisearch.models.document import DocumentsResults
from meilisearch.models.task import TaskInfo
from sqlalchemy import select

from pindb.config import CONFIGURATION
from pindb.database import session_maker
from pindb.database.pin import Pin

LOGGER: logging.Logger = logging.getLogger(name="pindb.search.update")

PIN_INDEX: Index = CONFIGURATION.meili_client.index(uid=CONFIGURATION.meilisearch_index)


def setup_index() -> None:
    LOGGER.info("Configuring Meilisearch pin index settings.")
    try:
        CONFIGURATION.meili_client.create_index(
            uid=CONFIGURATION.meilisearch_index, options={"primaryKey": "id"}
        )
    except Exception:
        pass  # Index already exists
    PIN_INDEX.update_searchable_attributes(
        ["name", "tags", "materials", "artists", "shops", "description"]
    )


def update_pin(pin: Pin) -> TaskInfo:
    LOGGER.info(msg=f"Updating Pin with ID: {pin.id}")
    return PIN_INDEX.add_documents(documents=[pin.document()])


def update_pins(pins: Iterable[Pin]) -> TaskInfo:
    LOGGER.info(msg=f"Updating Pins with IDs: {[pin.id for pin in pins]}")
    return PIN_INDEX.add_documents(documents=[pin.document() for pin in pins])


def delete_pin(pin_id: int) -> TaskInfo:
    LOGGER.info(f"Deleting Pin with ID: {pin_id} from index.")
    return PIN_INDEX.delete_document(pin_id)


def _get_all_meili_pin_ids() -> set[int]:
    from meilisearch.errors import MeilisearchApiError

    ids: set[int] = set()
    limit = 1000
    offset = 0
    while True:
        try:
            result: DocumentsResults = PIN_INDEX.get_documents(
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


def update_all() -> None:
    LOGGER.info(msg="Updating all pins.")
    with session_maker.begin() as session:
        pins: Sequence[Pin] = session.scalars(statement=select(Pin)).all()
        db_ids: set[int] = {pin.id for pin in pins}
        if pins:
            update_pins(pins=pins)
        meili_ids: set[int] = _get_all_meili_pin_ids()
        stale_ids: list[int] = list(meili_ids - db_ids)
        if stale_ids:
            LOGGER.info(f"Deleting {len(stale_ids)} stale documents from index.")
            PIN_INDEX.delete_documents(stale_ids)
