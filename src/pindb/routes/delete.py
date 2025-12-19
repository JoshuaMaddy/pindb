import logging

from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import select

from pindb.database import session_maker
from pindb.database.material import Material
from pindb.database.pin import Pin

router = APIRouter(prefix="/delete")

LOGGER = logging.getLogger("pindb.routes.delete")


@router.get(path="/pin/{id}")
def post_delete_pin(id: int) -> HTMLResponse:
    with session_maker.begin() as session:
        pin: Pin | None = session.scalar(statement=select(Pin).where(Pin.id == id))
        session.delete(instance=pin)

    return HTMLResponse(content="Success")


@router.get(path="/material/{id}")
def post_delete_material(id: int) -> HTMLResponse:
    with session_maker.begin() as session:
        material: Material | None = session.scalar(statement=select(Material).where(Material.id == id))
        session.delete(instance=material)

    return HTMLResponse(content="Success")
