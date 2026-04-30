"""Meilisearch index mocks for integration tests."""

from __future__ import annotations

import importlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.fixtures import core


@pytest.fixture(autouse=True)
def patch_meilisearch(monkeypatch) -> MagicMock:
    """
    Replace the module-level PIN_INDEX in both search modules with a MagicMock.
    Tests that need custom search results can configure mock_index.search.return_value.
    Add @pytest.mark.meili to use a real Meilisearch container instead.
    """
    su = core._search_update
    ss = core._search_search

    mock_index = MagicMock()
    mock_index.search = AsyncMock(
        return_value={
            "hits": [],
            "offset": 0,
            "limit": 20,
            "estimatedTotalHits": 0,
            "processingTimeMs": 1,
            "query": "",
        }
    )
    mock_index.add_documents = AsyncMock(return_value=MagicMock(task_uid=1))
    mock_index.delete_document = AsyncMock(return_value=MagicMock(task_uid=2))
    mock_index.delete_documents = AsyncMock(return_value=MagicMock(task_uid=3))
    mock_index.get_documents = AsyncMock(return_value=MagicMock(results=[], total=0))
    mock_index.update_searchable_attributes = AsyncMock(
        return_value=MagicMock(task_uid=4)
    )
    mock_index.update_filterable_attributes = AsyncMock(
        return_value=MagicMock(task_uid=5)
    )
    if hasattr(su, "PIN_INDEX"):
        monkeypatch.setattr(su, "PIN_INDEX", mock_index)
    for name in (
        "_pin_index",
        "_tags_index",
        "_artists_index",
        "_shops_index",
        "_pin_sets_index",
    ):
        if hasattr(su, name):
            monkeypatch.setattr(su, name, lambda: mock_index)
    monkeypatch.setattr(ss, "PIN_INDEX", mock_index)
    for name in ("TAGS_INDEX", "ARTISTS_INDEX", "SHOPS_INDEX", "PIN_SETS_INDEX"):
        if hasattr(su, name):
            monkeypatch.setattr(su, name, mock_index)

    if hasattr(su, "INDEX_BY_ENTITY_TYPE"):
        from pindb.database.entity_type import EntityType

        monkeypatch.setattr(
            su,
            "INDEX_BY_ENTITY_TYPE",
            {et: mock_index for et in EntityType},
        )

    try:
        _bulk_pin = importlib.import_module("pindb.routes.bulk.pin")
        if hasattr(_bulk_pin, "TAGS_INDEX"):
            monkeypatch.setattr(_bulk_pin, "TAGS_INDEX", mock_index)
    except ImportError:
        pass

    for module_name in ("pindb.routes.get.options", "pindb.routes.get.tag"):
        try:
            module = importlib.import_module(module_name)
            for name in (
                "PIN_INDEX",
                "TAGS_INDEX",
                "ARTISTS_INDEX",
                "SHOPS_INDEX",
                "PIN_SETS_INDEX",
            ):
                if hasattr(module, name):
                    monkeypatch.setattr(module, name, mock_index)
        except ImportError:
            pass

    return mock_index
