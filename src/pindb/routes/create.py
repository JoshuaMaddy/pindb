from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from pydantic import BeforeValidator
from sqlalchemy import select

from pindb.database import Material, Shop, Tag, session_maker
from pindb.database.link import Link
from pindb.database.pin import Pin
from pindb.file_handler import save_file
from pindb.model_utils import empty_str_list_to_none, empty_str_to_none, magnitude_to_mm
from pindb.models.acquisition_type import AcquisitionType
from pindb.models.funding_type import FundingType
from pindb.templates.create.material import material_form
from pindb.templates.create.pin import pin_form
from pindb.templates.create.shop import shop_form

router = APIRouter(prefix="/create")


@router.get("/pin")
def get_create_pin(request: Request) -> HTMLResponse:
    with session_maker.begin() as session:
        materials = session.scalars(select(Material)).all()
        shops = session.scalars(select(Shop)).all()
        tags = session.scalars(select(Tag)).all()

        return HTMLResponse(
            pin_form(
                post_url=request.url_for("post_create_pin"),
                materials=materials,
                shops=shops,
                tags=tags,
            )
        )


@router.post("/pin")
async def post_create_pin(
    request: Request,
    front_image: UploadFile = Form(),
    name: str = Form(),
    acquisition_type: AcquisitionType = Form(),
    material_ids: list[int] = Form(default_factory=list),
    shop_ids: list[int] = Form(default_factory=list),
    tag_ids: list[int] = Form(default_factory=list),
    number_produced: Annotated[
        int | None,
        Form(),
        BeforeValidator(empty_str_to_none),
    ] = None,
    limited_edition: bool | None = Form(default=None),
    release_date: Annotated[
        date | None,
        Form(),
        BeforeValidator(empty_str_to_none),
    ] = None,
    end_date: Annotated[
        date | None,
        Form(),
        BeforeValidator(empty_str_to_none),
    ] = None,
    funding_type: FundingType | None = Form(default=None),
    posts: int = Form(default=1),
    width: Annotated[
        str | None,
        Form(),
        BeforeValidator(empty_str_to_none),
    ] = None,
    height: Annotated[
        str | None,
        Form(),
        BeforeValidator(empty_str_to_none),
    ] = None,
    links: Annotated[
        list[str] | None,
        Form(),
        BeforeValidator(empty_str_list_to_none),
    ] = None,
    back_image: UploadFile | None = Form(default=None),
) -> HTMLResponse:
    back_image_guid: UUID | None = None
    front_image_guid: UUID = await save_file(front_image)

    if back_image:
        back_image_guid = await save_file(back_image)

    with session_maker.begin() as session:
        pin_materials = set(
            session.scalars(select(Material).where(Material.id.in_(material_ids))).all()
        )
        pin_shops = set(
            session.scalars(select(Shop).where(Shop.id.in_(shop_ids))).all()
        )
        pin_tags = set(session.scalars(select(Tag).where(Tag.id.in_(tag_ids))).all())
        new_links = {Link(path=link) for link in links} if links else set[Link]()

        print(width)

        new_pin = Pin(
            name=name,
            acquisition_type=acquisition_type,
            front_image_guid=front_image_guid,
            materials=pin_materials,
            shops=pin_shops,
            limited_edition=limited_edition,
            number_produced=number_produced,
            release_date=release_date,
            end_date=end_date,
            funding_type=funding_type,
            posts=posts,
            width=magnitude_to_mm(width) if width else width,  # type: ignore
            height=magnitude_to_mm(height) if height else height,  # type: ignore
            back_image_guid=back_image_guid,
            description=None,
            artists=set(),
            sets=set(),
            tags=pin_tags,
            links=new_links,
        )

        session.add(new_pin)
        session.flush()
        pin_id = new_pin.id

    return HTMLResponse(
        headers={
            "HX-Redirect": str(
                request.url_for(
                    "get_pin",
                    id=pin_id,
                )
            )
        }
    )


@router.get("/material")
def get_create_material(request: Request) -> HTMLResponse:
    return HTMLResponse(material_form(post_url=request.url_for("post_create_material")))


@router.post("/material")
def post_create_material(
    request: Request,
    name: str = Form(),
) -> HTMLResponse:
    with session_maker.begin() as session:
        session.add(Material(name=name))

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_create_material"))}
    )


@router.get("/shop")
def get_create_shop(request: Request) -> HTMLResponse:
    return HTMLResponse(shop_form(post_url=request.url_for("post_create_shop")))


@router.post("/shop")
def post_create_shop(
    request: Request,
    name: str = Form(),
    description: Annotated[
        str | None,
        Form(),
        BeforeValidator(empty_str_to_none),
    ] = None,
    links: Annotated[
        list[str] | None,
        Form(),
        BeforeValidator(empty_str_list_to_none),
    ] = None,
) -> HTMLResponse:
    with session_maker.begin() as session:
        new_links = {Link(path=link) for link in links} if links else set[Link]()

        session.add(
            Shop(
                name=name,
                description=description,
                links=new_links,
            )
        )

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_create_shop"))}
    )


@router.get("/tag")
def get_create_tag(request: Request) -> HTMLResponse:
    return HTMLResponse(shop_form(post_url=request.url_for("post_create_tag")))


@router.post("/tag")
def post_create_tag(
    request: Request,
    name: str = Form(),
) -> HTMLResponse:
    with session_maker.begin() as session:
        session.add(Tag(name=name))

    return HTMLResponse(headers={"HX-Redirect": str(request.url_for("get_create_tag"))})
