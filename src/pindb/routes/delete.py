import logging

from fastapi import Depends
from fastapi.responses import RedirectResponse
from fastapi.routing import APIRouter
from sqlalchemy import select

from pindb.auth import require_admin
from pindb.database import session_maker
from pindb.database.artist import Artist
from pindb.database.material import Material
from pindb.database.pin import Pin
from pindb.database.shop import Shop
from pindb.database.tag import Tag
from pindb.search.update import delete_pin as delete_pin_from_index

router = APIRouter(prefix="/delete", dependencies=[Depends(require_admin)])

LOGGER = logging.getLogger("pindb.routes.delete")


@router.get(path="/pin/{id}")
def post_delete_pin(id: int) -> RedirectResponse:
    with session_maker.begin() as session:
        pin: Pin | None = session.scalar(statement=select(Pin).where(Pin.id == id))
        session.delete(instance=pin)

    delete_pin_from_index(pin_id=id)
    return RedirectResponse(url="/", status_code=303)


@router.post(path="/material/{id}")
def post_delete_material(id: int) -> RedirectResponse:
    with session_maker.begin() as session:
        material: Material | None = session.scalar(
            statement=select(Material).where(Material.id == id)
        )
        session.delete(instance=material)

    return RedirectResponse(url="/", status_code=303)


@router.get(path="/artist/{id}")
def post_delete_artist(id: int) -> RedirectResponse:
    with session_maker.begin() as session:
        artist: Artist | None = session.scalar(
            statement=select(Artist).where(Artist.id == id)
        )
        session.delete(instance=artist)

    return RedirectResponse(url="/", status_code=303)


@router.post(path="/tag/{id}")
def post_delete_tag(id: int) -> RedirectResponse:
    with session_maker.begin() as session:
        tag: Tag | None = session.scalar(statement=select(Tag).where(Tag.id == id))
        session.delete(instance=tag)

    return RedirectResponse(url="/", status_code=303)


@router.post(path="/shop/{id}")
def post_delete_shop(id: int) -> RedirectResponse:
    with session_maker.begin() as session:
        shop: Shop | None = session.scalar(statement=select(Shop).where(Shop.id == id))
        session.delete(instance=shop)

    return RedirectResponse(url="/", status_code=303)
