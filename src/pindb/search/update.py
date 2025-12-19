import logging
from typing import Iterable

from meilisearch.models.task import TaskInfo
from sqlalchemy import select

from pindb.config import CONFIGURATION
from pindb.database import session_maker
from pindb.database.pin import Pin

LOGGER = logging.getLogger("pindb.search.update")

PIN_INDEX = CONFIGURATION.meili_client.index(CONFIGURATION.meilisearch_index)


def update_pin(pin: Pin) -> TaskInfo:
    LOGGER.info(f"Updating Pin with ID: {pin.id}")
    return PIN_INDEX.add_documents(documents=[pin.document()])


def update_pins(pins: Iterable[Pin]) -> TaskInfo:
    LOGGER.info(f"Updating Pins with IDs: {[pin.id for pin in pins]}")
    return PIN_INDEX.add_documents(documents=[pin.document() for pin in pins])


def update_all() -> TaskInfo:
    LOGGER.info("Updating all pins.")
    with session_maker.begin() as session:
        return update_pins(session.scalars(select(Pin)).all())
