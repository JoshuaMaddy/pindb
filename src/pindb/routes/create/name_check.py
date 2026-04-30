"""HTMX duplicate-name check endpoint for editor create/edit forms."""

from fastapi import Query
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

from pindb.database import async_session_maker
from pindb.routes._name_check import (
    NameCheckKind,
    duplicate_name_response,
    empty_name_check_response,
    normalized_name_exists,
    normalized_name_key,
)

router = APIRouter()


@router.get(path="/check-name", response_model=None)
async def get_create_check_name(
    kind: NameCheckKind = Query(),
    name: str = Query(default=""),
    exclude_id: int | None = Query(default=None),
) -> HTMLResponse:
    normalized_name: str = normalized_name_key(name=name)
    if not normalized_name:
        return empty_name_check_response()

    async with async_session_maker() as session:
        exists: bool = await normalized_name_exists(
            session=session,
            kind=kind,
            normalized_name=normalized_name,
            exclude_id=exclude_id,
            global_pin_sets=kind == NameCheckKind.pin_set,
        )

    if not exists:
        return empty_name_check_response()
    return duplicate_name_response(name=name)
