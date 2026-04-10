import logging

from fastapi import Depends
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import select

from pindb.auth import require_admin
from pindb.database import session_maker
from pindb.database.artist import Artist
from pindb.database.material import Material
from pindb.database.pin import Pin
from pindb.search.update import delete_pin as delete_pin_from_index

router = APIRouter(prefix="/delete", dependencies=[Depends(require_admin)])

LOGGER = logging.getLogger("pindb.routes.delete")


@router.get(path="/pin/{id}")
def post_delete_pin(id: int) -> HTMLResponse:
    with session_maker.begin() as session:
        pin: Pin | None = session.scalar(statement=select(Pin).where(Pin.id == id))
        session.delete(instance=pin)

    delete_pin_from_index(pin_id=id)
    return HTMLResponse(content="Success")


@router.get(path="/material/{id}")
def post_delete_material(id: int) -> HTMLResponse:
    with session_maker.begin() as session:
        material: Material | None = session.scalar(
            statement=select(Material).where(Material.id == id)
        )
        session.delete(instance=material)

    return HTMLResponse(content="Success")


@router.get(path="/artist/{id}")
def post_delete_artist(id: int) -> HTMLResponse:
    with session_maker.begin() as session:
        artist: Artist | None = session.scalar(
            statement=select(Artist).where(Artist.id == id)
        )
        session.delete(instance=artist)

    return HTMLResponse(content="Success")
