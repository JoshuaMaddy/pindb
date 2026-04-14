from fastapi import Query
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter

from pindb.database.entity_type import EntityType
from pindb.search.search import (
    ARTISTS_INDEX,
    PIN_SETS_INDEX,
    SHOPS_INDEX,
    TAGS_INDEX,
    search_entity_options,
)

router = APIRouter()

_ALLOWED_ENTITY_TYPES: frozenset[EntityType] = frozenset(
    {
        EntityType.shop,
        EntityType.tag,
        EntityType.artist,
        EntityType.pin_set,
    }
)

_INDEX_MAP = {
    EntityType.shop: SHOPS_INDEX,
    EntityType.tag: TAGS_INDEX,
    EntityType.artist: ARTISTS_INDEX,
    EntityType.pin_set: PIN_SETS_INDEX,
}


@router.get(path="/options/{entity_type}")
def get_entity_options(
    entity_type: EntityType,
    q: str = Query(default=""),
) -> JSONResponse:
    if entity_type not in _ALLOWED_ENTITY_TYPES:
        return JSONResponse(content=[])
    index = _INDEX_MAP[entity_type]
    return JSONResponse(content=search_entity_options(index=index, query=q))
