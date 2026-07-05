"""
FastAPI routes: `routes/search.py`.
"""

from fastapi import Request
from fastapi.routing import APIRouter
from htpy.starlette import HtpyResponse

from pindb.database import async_session_maker
from pindb.database.pin import Pin
from pindb.search.search import search_pin
from pindb.templates.search.pin import search_pin_page, search_results

router = APIRouter(prefix="/search")


@router.get(path="/pin")
async def get_search_pin(
    request: Request,
    q: str | None = None,
) -> HtpyResponse:
    query: str = (q or "").strip()
    pins: list[Pin] | None = None
    if query:
        async with async_session_maker() as session:
            pins = await search_pin(query=query, session=session)

    # Live-search typing (HTMX) swaps just the results container; a full page
    # load — including a bookmarked/shared ?q= URL — renders results inline.
    if request.headers.get("HX-Request"):
        return HtpyResponse(search_results(request=request, pins=pins, query=query))

    return HtpyResponse(
        search_pin_page(request=request, initial_query=query or None, pins=pins)
    )
