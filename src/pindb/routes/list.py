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


@router.get("/")
def get_list_index(request: Request) -> HTMLResponse:
    return HTMLResponse(list_index_page(request=request))


@router.get("/shops")
def get_list_shops(request: Request) -> HTMLResponse:
    with session_maker.begin() as session:
        shops = session.scalars(select(Shop).order_by(Shop.name.asc())).all()

        return HTMLResponse(shops_list(request=request, shops=shops))


@router.get("/pin_sets")
def get_list_pin_sets(request: Request) -> HTMLResponse:
    with session_maker.begin() as session:
        pin_sets = session.scalars(select(PinSet).order_by(PinSet.name.asc())).all()

        return HTMLResponse(pin_sets_list(request=request, pin_sets=pin_sets))


@router.get("/materials")
def get_list_materials(request: Request) -> HTMLResponse:
    with session_maker.begin() as session:
        materials = session.scalars(
            select(Material).order_by(Material.name.asc())
        ).all()

        return HTMLResponse(materials_list(request=request, materials=materials))


@router.get("/tags")
def get_list_tags(request: Request) -> HTMLResponse:
    with session_maker.begin() as session:
        tags = session.scalars(select(Tag).order_by(Tag.name.asc())).all()

        return HTMLResponse(tags_list(request=request, tags=tags))
