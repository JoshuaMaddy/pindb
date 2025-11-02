from fastapi import Form, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import func, select

from pindb.database import Pin, session_maker
from pindb.templates.components.pin_grid import pin_grid
from pindb.templates.search.pin import search_pin_form

router = APIRouter(prefix="/search")


@router.get("/pin")
def get_search_pin(
    request: Request,
) -> HTMLResponse:
    return HTMLResponse(search_pin_form(post_url=request.url_for("post_search_pin")))


@router.post("/pin")
def post_search_pin(
    request: Request,
    search: str = Form(),
) -> HTMLResponse:
    with session_maker.begin() as session:
        pins = session.scalars(
            select(Pin).where(func.similarity(Pin.name, search) > 0.3).limit(10)
        ).all()
        return HTMLResponse(pin_grid(request=request, pins=pins))
