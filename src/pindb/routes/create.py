from fastapi import Form, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import select

from pindb.database import Material, Shop, session_maker
from pindb.models.acquisition_type import AcquisitionType
from pindb.templates.create.material import material_form
from pindb.templates.create.pin import pin_form
from pindb.templates.create.shop import shop_form

router = APIRouter(prefix="/create")


@router.get("/pin")
def get_create_pin(request: Request) -> HTMLResponse:
    with session_maker.begin() as session:
        materials = session.scalars(select(Material)).all()
        shops = session.scalars(select(Shop)).all()

        return HTMLResponse(
            pin_form(
                post_url=request.url_for("post_create_pin"),
                materials=materials,
                shops=shops,
            )
        )


@router.post("/pin")
def post_create_pin(
    request: Request,
    name: str = Form(),
    acquisition_type: AcquisitionType = Form(),
    material_ids: list[int] = Form(),
    shop_ids: list[int] = Form(),
) -> None:
    print(name, acquisition_type, material_ids, shop_ids)


@router.get("/material")
def get_create_material(request: Request) -> HTMLResponse:
    return HTMLResponse(material_form(post_url=request.url_for("post_create_material")))


@router.post("/material")
def post_create_material(request: Request, name: str = Form()) -> HTMLResponse:
    with session_maker.begin() as session:
        session.add(Material(name=name))

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_create_material"))}
    )


@router.get("/shop")
def get_create_shop(request: Request) -> HTMLResponse:
    return HTMLResponse(shop_form(post_url=request.url_for("post_create_shop")))


@router.post("/shop")
def post_create_shop(request: Request, name: str = Form()) -> HTMLResponse:
    with session_maker.begin() as session:
        session.add(Shop(name=name))

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_create_shop"))}
    )
