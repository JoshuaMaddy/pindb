"""Integration tests for /search/pin — uses the mocked Meilisearch index."""

import pytest

from tests.factories.pin import PinFactory


@pytest.mark.integration
class TestSearchPin:
    def test_get_search_page_returns_200(self, client):
        response = client.get("/search/pin")
        assert response.status_code == 200

    def test_empty_search_returns_200(self, client):
        response = client.post("/search/pin", data={"search": ""})
        assert response.status_code == 200

    def test_search_with_no_hits_shows_empty_state(self, client, patch_meilisearch):
        patch_meilisearch.search.return_value = {
            "hits": [],
            "offset": 0,
            "limit": 20,
            "estimatedTotalHits": 0,
            "processingTimeMs": 1,
            "query": "nonexistent",
        }
        response = client.post("/search/pin", data={"search": "nonexistent"})
        assert response.status_code == 200

    def test_search_with_hits_shows_pin_names(
        self, client, db_session, patch_meilisearch
    ):
        pin = PinFactory(name="Rare Holographic Pin")
        patch_meilisearch.search.return_value = {
            "hits": [
                {
                    "id": pin.id,  # ty:ignore[unresolved-attribute]
                    "name": pin.name,
                    "shops": [],
                    "tags": [],
                    "artists": [],
                    "description": None,
                }
            ],
            "offset": 0,
            "limit": 20,
            "estimatedTotalHits": 1,
            "processingTimeMs": 2,
            "query": "holographic",
        }
        response = client.post("/search/pin", data={"search": "holographic"})
        assert response.status_code == 200
        assert "Rare Holographic Pin" in response.text
