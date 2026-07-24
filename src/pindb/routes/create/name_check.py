"""HTMX duplicate-name + blacklist check endpoint for editor create/edit forms."""

from fastapi import Query
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

from pindb.blacklist import BlacklistMatch, find_blacklist_match
from pindb.database import BlacklistEntityType, async_session_maker
from pindb.routes._name_check import (
    NameCheckKind,
    blacklist_match_response,
    duplicate_name_response,
    empty_name_check_response,
    normalized_name_exists,
    normalized_name_key,
)

router = APIRouter()

_BLACKLIST_KINDS: dict[NameCheckKind, BlacklistEntityType] = {
    NameCheckKind.shop: BlacklistEntityType.shop,
    NameCheckKind.artist: BlacklistEntityType.artist,
}


@router.get(path="/check-name", response_model=None)
async def get_create_check_name(
    kind: NameCheckKind = Query(),
    name: str = Query(default=""),
    exclude_id: int | None = Query(default=None),
) -> HTMLResponse:
    normalized_name: str = normalized_name_key(name=name)
    if not normalized_name:
        return empty_name_check_response()

    blacklist_entity_type: BlacklistEntityType | None = _BLACKLIST_KINDS.get(kind)
    blacklist_match: BlacklistMatch | None = None

    async with async_session_maker() as session:
        exists: bool = await normalized_name_exists(
            session=session,
            kind=kind,
            normalized_name=normalized_name,
            exclude_id=exclude_id,
            global_pin_sets=kind == NameCheckKind.pin_set,
        )
        if not exists and blacklist_entity_type is not None:
            blacklist_match = await find_blacklist_match(
                session=session,
                entity_type=blacklist_entity_type,
                candidates=[name],
            )

    if exists:
        return duplicate_name_response(name=name)
    if blacklist_match is not None:
        return blacklist_match_response(match=blacklist_match)
    return empty_name_check_response()
