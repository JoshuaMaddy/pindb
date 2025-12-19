from fastapi import Form, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter

from pindb.database import session_maker
from pindb.search.search import search_pin
from pindb.templates.components.pin_grid import pin_grid
from pindb.templates.search.pin import search_pin_page

router = APIRouter(prefix="/search")


@router.get("/pin")
def get_search_pin(
    request: Request,
) -> HTMLResponse:
    return HTMLResponse(search_pin_page(post_url=request.url_for("post_search_pin")))


@router.post("/pin")
def post_search_pin(
    request: Request,
    search: str = Form(),
) -> HTMLResponse:
    with session_maker.begin() as session:
        pins = search_pin(query=search, session=session)
        return HTMLResponse(pin_grid(request=request, pins=pins))
