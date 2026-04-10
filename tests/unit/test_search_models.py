"""Unit tests for PinSearchResult.from_raw() in src/pindb/search/search.py."""

import pytest

from pindb.search.search import PinSearchResult


@pytest.mark.unit
class TestPinSearchResultFromRaw:
    def _minimal_raw(self, **overrides) -> dict:
        base = {
            "hits": [],
            "offset": 0,
            "limit": 20,
            "estimatedTotalHits": 0,
            "processingTimeMs": 5,
            "query": "test",
        }
        base.update(overrides)
        return base

    def test_minimal_result(self):
        raw = self._minimal_raw()
        result = PinSearchResult.from_raw(raw)
        assert result.hits == []
        assert result.offset == 0
        assert result.limit == 20
        assert result.processing_time_ms == 5
        assert result.query == "test"

    def test_camel_case_keys_converted(self):
        # processingTimeMs → processing_time_ms, estimatedTotalHits → estimated_total_hits
        raw = self._minimal_raw(estimatedTotalHits=42, processingTimeMs=3)
        result = PinSearchResult.from_raw(raw)
        assert result.estimated_total_hits == 42
        assert result.processing_time_ms == 3

    def test_hits_parsed(self):
        raw = self._minimal_raw(
            hits=[
                {
                    "id": 7,
                    "name": "Pikachu Pin",
                    "shops": ["Pokemon Center"],
                    "materials": ["enamel"],
                    "tags": ["pokemon"],
                    "artists": ["some artist"],
                    "description": "A great pin",
                }
            ]
        )
        result = PinSearchResult.from_raw(raw)
        assert len(result.hits) == 1
        hit = result.hits[0]
        assert hit.id == 7
        assert hit.name == "Pikachu Pin"
        assert hit.shops == ["Pokemon Center"]
        assert hit.materials == ["enamel"]
        assert hit.tags == ["pokemon"]
        assert hit.artists == ["some artist"]
        assert hit.description == "A great pin"

    def test_hit_optional_fields_default(self):
        raw = self._minimal_raw(
            hits=[{"id": 1, "name": "Pin", "shops": [], "materials": []}]
        )
        result = PinSearchResult.from_raw(raw)
        hit = result.hits[0]
        assert hit.tags == []
        assert hit.artists == []
        assert hit.description is None

    def test_optional_pagination_fields_none_when_absent(self):
        raw = self._minimal_raw()
        result = PinSearchResult.from_raw(raw)
        assert result.total_hits is None
        assert result.total_pages is None
        assert result.hits_per_page is None
        assert result.page is None

    def test_pagination_fields_parsed_when_present(self):
        raw = self._minimal_raw(totalHits=100, totalPages=5, hitsPerPage=20, page=2)
        result = PinSearchResult.from_raw(raw)
        assert result.total_hits == 100
        assert result.total_pages == 5
        assert result.hits_per_page == 20
        assert result.page == 2
