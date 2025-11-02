from uuid import UUID

from fastapi import Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.routing import APIRouter

from pindb.config import CONFIGURATION
from pindb.database import Material, Pin, Shop, Tag, session_maker
from pindb.database.pin_set import PinSet
from pindb.templates.get.material import material_page
from pindb.templates.get.pin import pin_page
from pindb.templates.get.pin_set import pin_set_page
from pindb.templates.get.shop import shop_page
from pindb.templates.get.tag import tag_page

router = APIRouter(prefix="/get")


@router.get("/image/{guid}", response_model=None)
def get_image(guid: UUID) -> FileResponse | None:
    image_path = (CONFIGURATION.image_directory / str(guid)).resolve()

    if not image_path.exists() or not image_path.is_file():
        return None

    return FileResponse(path=image_path, media_type="image")


@router.get("/pin/{id}")
def get_pin(
    request: Request,
    id: int,
) -> HTMLResponse:
    with session_maker.begin() as session:
        pin_obj = session.get(Pin, id)

        if not pin_obj:
            return None

        return HTMLResponse(pin_page(request=request, pin=pin_obj))


@router.get("/shop/{id}")
def get_shop(
    request: Request,
    id: int,
) -> HTMLResponse:
    with session_maker.begin() as session:
        shop_obj = session.get(Shop, id)

        if not shop_obj:
            return None

        return HTMLResponse(shop_page(request=request, shop=shop_obj))


@router.get("/material/{id}")
def get_material(
    request: Request,
    id: int,
) -> HTMLResponse:
    with session_maker.begin() as session:
        material_obj = session.get(Material, id)

        if not material_obj:
            return None

        return HTMLResponse(material_page(request=request, material=material_obj))


@router.get("/tag/{id}", response_model=None)
def get_tag(
    request: Request,
    id: int,
) -> HTMLResponse:
    with session_maker.begin() as session:
        tag_obj = session.get(Tag, id)

        if not tag_obj:
            return None

        return HTMLResponse(tag_page(request=request, tag=tag_obj))


@router.get("/pin_set/{id}", response_model=None)
def get_pin_set(
    request: Request,
    id: int,
) -> HTMLResponse:
    with session_maker.begin() as session:
        pin_set_obj = session.get(PinSet, id)

        if not pin_set_obj:
            return None

        return HTMLResponse(pin_set_page(request=request, pin_set=pin_set_obj))
