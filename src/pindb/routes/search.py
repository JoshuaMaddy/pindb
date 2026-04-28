"""
FastAPI routes: `routes/search.py`.
"""

from fastapi import Form, Request
from fastapi.routing import APIRouter
from htpy.starlette import HtpyResponse

from pindb.database import session_maker
from pindb.database.pin import Pin
from pindb.search.search import search_pin
from pindb.templates.components.pins.pin_grid import pin_grid
from pindb.templates.search.pin import search_pin_page

router = APIRouter(prefix="/search")


@router.get(path="/pin")
def get_search_pin(
    request: Request,
    q: str | None = None,
) -> HtpyResponse:
    return HtpyResponse(
        search_pin_page(
            post_url=request.url_for("post_search_pin"),
            request=request,
            initial_query=q,
        )
    )


@router.post(path="/pin")
def post_search_pin(
    request: Request,
    search: str = Form(default=""),
) -> HtpyResponse:
    with session_maker() as session:
        pins: list[Pin] | None = search_pin(query=search, session=session)
    return HtpyResponse(pin_grid(request=request, pins=pins))
