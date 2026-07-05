"""Unit tests for global-only filtering in search_pin_sets — no DB/Meili needed."""

from unittest.mock import AsyncMock

import pytest

from pindb.search import search as search_module

_EMPTY_RESULT = {
    "hits": [],
    "offset": 0,
    "limit": 100,
    "estimatedTotalHits": 0,
    "processingTimeMs": 1,
    "query": "x",
}


@pytest.mark.unit
class TestSearchPinSetsGlobalOnly:
    async def test_global_only_forwards_owner_id_filter(self, monkeypatch):
        mock_search = AsyncMock(return_value=_EMPTY_RESULT)
        monkeypatch.setattr(search_module.PIN_SETS_INDEX, "search", mock_search)

        result, total = await search_module.search_pin_sets(
            query="x", session=AsyncMock(), global_only=True
        )

        assert result == []
        mock_search.assert_awaited_once()
        call = mock_search.await_args
        assert call is not None
        assert call.kwargs.get("filter") == "owner_id IS NULL"

    async def test_default_passes_no_filter(self, monkeypatch):
        mock_search = AsyncMock(return_value=_EMPTY_RESULT)
        monkeypatch.setattr(search_module.PIN_SETS_INDEX, "search", mock_search)

        await search_module.search_pin_sets(query="x", session=AsyncMock())

        mock_search.assert_awaited_once()
        call = mock_search.await_args
        assert call is not None
        # Default path uses the no-filter branch of _search_index.
        assert "filter" not in call.kwargs
