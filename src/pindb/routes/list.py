from typing import Sequence
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import select

from pindb.database import Shop, session_maker
from pindb.database.material import Material
from pindb.database.pin_set import PinSet
from pindb.database.tag import Tag
from pindb.templates.list.index import list_index_page
from pindb.templates.list.materials import materials_list
from pindb.templates.list.pin_sets import pin_sets_list
from pindb.templates.list.shops import shops_list
from pindb.templates.list.tags import tags_list

router = APIRouter(prefix="/list")


@router.get(path="/")
def get_list_index(request: Request) -> HTMLResponse:
    return HTMLResponse(content=list_index_page(request=request))


@router.get(path="/shops")
def get_list_shops(request: Request) -> HTMLResponse:
    with session_maker.begin() as session:
        shops: Sequence[Shop] = session.scalars(
            statement=select(Shop).order_by(Shop.name.asc())
        ).all()

        return HTMLResponse(content=shops_list(request=request, shops=shops))


@router.get(path="/pin_sets")
def get_list_pin_sets(request: Request) -> HTMLResponse:
    with session_maker.begin() as session:
        pin_sets: Sequence[PinSet] = session.scalars(
            statement=select(PinSet).order_by(PinSet.name.asc())
        ).all()

        return HTMLResponse(content=pin_sets_list(request=request, pin_sets=pin_sets))


@router.get(path="/materials")
def get_list_materials(request: Request) -> HTMLResponse:
    with session_maker.begin() as session:
        materials: Sequence[Material] = session.scalars(
            statement=select(Material).order_by(Material.name.asc())
        ).all()

        return HTMLResponse(
            content=materials_list(request=request, materials=materials)
        )


@router.get(path="/tags")
def get_list_tags(request: Request) -> HTMLResponse:
    with session_maker.begin() as session:
        tags: Sequence[Tag] = session.scalars(
            statement=select(Tag).order_by(Tag.name.asc())
        ).all()

        return HTMLResponse(content=tags_list(request=request, tags=tags))
