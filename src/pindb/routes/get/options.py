"""
FastAPI routes: `routes/get/options.py`.
"""

from fastapi import Depends, Query
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter

from pindb.auth import require_editor
from pindb.database.entity_type import EntityType
from pindb.search.search import (
    ARTISTS_INDEX,
    PIN_INDEX,
    PIN_SETS_INDEX,
    SHOPS_INDEX,
    TAGS_INDEX,
    search_entity_options,
)

# Options feed the multi-select autocompletes on create/edit/bulk forms, which
# are all editor-gated. Pending entities live in Meili (so editors see them with
# the (P) prefix) and this endpoint reads Meili directly with no DB re-hydration,
# so it must be editor-gated too — otherwise guests/regular users could pull
# pending items straight from the index.
router = APIRouter(dependencies=[Depends(require_editor)])

_ALLOWED_ENTITY_TYPES: frozenset[EntityType] = frozenset(
    {
        EntityType.shop,
        EntityType.tag,
        EntityType.artist,
        EntityType.pin_set,
        EntityType.pin,
    }
)

_INDEX_MAP = {
    EntityType.shop: SHOPS_INDEX,
    EntityType.tag: TAGS_INDEX,
    EntityType.artist: ARTISTS_INDEX,
    EntityType.pin_set: PIN_SETS_INDEX,
    EntityType.pin: PIN_INDEX,
}


# Autocomplete results go stale the moment someone else creates/renames/deletes
# the entity being searched; a client- or shared-cache hit would silently show
# an editor outdated options. Not worth caching for the perf gain, so results
# are never stored — each keystroke's query is normally unique anyway.
_NO_STORE_HEADERS = {"Cache-Control": "no-store"}


@router.get(path="/options/{entity_type}")
async def get_entity_options(
    entity_type: EntityType,
    q: str = Query(default=""),
    exclude: list[int] = Query(default=[]),
) -> JSONResponse:
    if entity_type not in _ALLOWED_ENTITY_TYPES:
        return JSONResponse(content=[], headers=_NO_STORE_HEADERS)
    index = _INDEX_MAP[entity_type]
    results = await search_entity_options(index=index, query=q, exclude_ids=exclude)
    return JSONResponse(content=results, headers=_NO_STORE_HEADERS)
