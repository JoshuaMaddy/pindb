import logging

from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import select

from pindb.database import session_maker
from pindb.database.material import Material
from pindb.database.pin import Pin

router = APIRouter(prefix="/delete")

LOGGER = logging.getLogger("pindb.routes.delete")


@router.get("/pin/{id}")
def post_delete_pin(id: int) -> HTMLResponse:
    with session_maker.begin() as session:
        pin = session.scalar(select(Pin).where(Pin.id == id))
        session.delete(pin)

    return HTMLResponse(content="Success")


@router.get("/material/{id}")
def post_delete_material(id: int) -> HTMLResponse:
    with session_maker.begin() as session:
        material = session.scalar(select(Material).where(Material.id == id))
        session.delete(material)

    return HTMLResponse(content="Success")
