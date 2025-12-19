import logging
from datetime import date
from typing import Annotated, Sequence
from uuid import UUID

from fastapi import Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from pydantic import BeforeValidator
from sqlalchemy import select

from pindb.database import Material, Shop, Tag, session_maker
from pindb.database.currency import Currency
from pindb.database.link import Link
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.file_handler import save_file
from pindb.model_utils import empty_str_list_to_none, empty_str_to_none, magnitude_to_mm
from pindb.models.acquisition_type import AcquisitionType
from pindb.models.funding_type import FundingType
from pindb.templates.create_and_edit.index import create_index
from pindb.templates.create_and_edit.material import material_form
from pindb.templates.create_and_edit.pin import pin_form
from pindb.templates.create_and_edit.pin_set import pin_set_form
from pindb.templates.create_and_edit.shop import shop_form
from pindb.templates.create_and_edit.tag import tag_form

router = APIRouter(prefix="/create")

LOGGER = logging.getLogger(name="pindb.search.update")


@router.get(path="/")
def get_create_index(request: Request) -> HTMLResponse:
    return HTMLResponse(content=create_index(request=request))


@router.get(path="/pin")
def get_create_pin(request: Request) -> HTMLResponse:
    with session_maker.begin() as session:
        materials: Sequence[Material] = session.scalars(
            statement=select(Material)
        ).all()
        shops: Sequence[Shop] = session.scalars(statement=select(Shop)).all()
        tags: Sequence[Tag] = session.scalars(statement=select(Tag)).all()
        pin_sets: Sequence[PinSet] = session.scalars(statement=select(PinSet)).all()
        currencies: Sequence[Currency] = session.scalars(
            statement=select(Currency)
        ).all()

        return HTMLResponse(
            content=pin_form(
                post_url=request.url_for("post_create_pin"),
                materials=materials,
                shops=shops,
                pin_sets=pin_sets,
                tags=tags,
                currencies=currencies,
            )
        )


@router.post(path="/pin")
async def post_create_pin(
    request: Request,
    front_image: UploadFile = Form(),
    name: str = Form(),
    acquisition_type: AcquisitionType = Form(),
    original_price: float = Form(default=0),
    currency_id: int = Form(default=840),
    material_ids: list[int] = Form(default_factory=list),
    shop_ids: list[int] = Form(default_factory=list),
    tag_ids: list[int] = Form(default_factory=list),
    pin_sets_ids: list[int] = Form(default_factory=list),
    number_produced: Annotated[
        int | None,
        Form(),
        BeforeValidator(func=empty_str_to_none),
    ] = None,
    limited_edition: bool | None = Form(default=None),
    release_date: Annotated[
        date | None,
        Form(),
        BeforeValidator(func=empty_str_to_none),
    ] = None,
    end_date: Annotated[
        date | None,
        Form(),
        BeforeValidator(func=empty_str_to_none),
    ] = None,
    funding_type: FundingType | None = Form(default=None),
    posts: int = Form(default=1),
    width: Annotated[
        str | None,
        Form(),
        BeforeValidator(func=empty_str_to_none),
    ] = None,
    height: Annotated[
        str | None,
        Form(),
        BeforeValidator(func=empty_str_to_none),
    ] = None,
    links: Annotated[
        list[str] | None,
        Form(),
        BeforeValidator(func=empty_str_list_to_none),
    ] = None,
    back_image: UploadFile | None = Form(default=None),
) -> HTMLResponse:
    LOGGER.info(msg=f"Creating Pin with form: {await request.form()}")

    back_image_guid: UUID | None = None
    front_image_guid: UUID = await save_file(file=front_image)

    if back_image:
        back_image_guid: UUID = await save_file(file=back_image)

    with session_maker.begin() as session:
        pin_materials: set[Material] = set(
            session.scalars(
                statement=select(Material).where(Material.id.in_(other=material_ids))
            ).all()
        )
        pin_shops: set[Shop] = set(
            session.scalars(
                statement=select(Shop).where(Shop.id.in_(other=shop_ids))
            ).all()
        )
        pin_tags: set[Tag] = set(
            session.scalars(
                statement=select(Tag).where(Tag.id.in_(other=tag_ids))
            ).all()
        )
        pin_sets: set[PinSet] = set(
            session.scalars(
                statement=select(PinSet).where(PinSet.id.in_(other=pin_sets_ids))
            ).all()
        )
        currency: Currency = session.get_one(entity=Currency, ident=currency_id)
        new_links: set[Link] = (
            {Link(path=link) for link in links} if links else set[Link]()
        )

        print(width)

        new_pin = Pin(
            name=name,
            acquisition_type=acquisition_type,
            front_image_guid=front_image_guid,
            original_price=original_price,
            currency=currency,
            materials=pin_materials,
            shops=pin_shops,
            limited_edition=limited_edition,
            number_produced=number_produced,
            release_date=release_date,
            end_date=end_date,
            funding_type=funding_type,
            posts=posts,
            width=magnitude_to_mm(magnitude=width) if width else width,  # type: ignore
            height=magnitude_to_mm(magnitude=height) if height else height,  # type: ignore
            back_image_guid=back_image_guid,
            description=None,
            artists=set(),
            sets=pin_sets,
            tags=pin_tags,
            links=new_links,
        )

        session.add(instance=new_pin)
        session.flush()
        pin_id: int = new_pin.id

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


@router.get(path="/material")
def get_create_material(request: Request) -> HTMLResponse:
    return HTMLResponse(
        content=material_form(post_url=request.url_for("post_create_material"))
    )


@router.post(path="/material")
async def post_create_material(
    request: Request,
    name: str = Form(),
) -> HTMLResponse:
    LOGGER.info(msg=f"Creating Material with {await request.form()}")

    with session_maker.begin() as session:
        material = Material(name=name)

        session.add(instance=material)
        session.flush()
        material_id = material.id

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_material", id=material_id))}
    )


@router.get(path="/shop")
def get_create_shop(request: Request) -> HTMLResponse:
    return HTMLResponse(content=shop_form(post_url=request.url_for("post_create_shop")))


@router.post(path="/shop")
def post_create_shop(
    request: Request,
    name: str = Form(),
    description: Annotated[
        str | None,
        Form(),
        BeforeValidator(func=empty_str_to_none),
    ] = None,
    links: Annotated[
        list[str] | None,
        Form(),
        BeforeValidator(func=empty_str_list_to_none),
    ] = None,
) -> HTMLResponse:
    with session_maker.begin() as session:
        new_links: set[Link] = (
            {Link(path=link) for link in links} if links else set[Link]()
        )

        shop = Shop(
            name=name,
            description=description,
            links=new_links,
        )

        session.add(instance=shop)
        session.flush()
        shop_id = shop.id

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_shop", id=shop_id))}
    )


@router.get(path="/tag")
def get_create_tag(request: Request) -> HTMLResponse:
    return HTMLResponse(content=tag_form(post_url=request.url_for("post_create_tag")))


@router.post(path="/tag")
def post_create_tag(
    request: Request,
    name: str = Form(),
) -> HTMLResponse:
    with session_maker.begin() as session:
        tag = Tag(name=name)

        session.add(instance=tag)
        session.flush()
        tag_id = tag.id

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_tag", id=tag_id))}
    )


@router.get(path="/pin_set")
def get_create_pin_set(request: Request) -> HTMLResponse:
    return HTMLResponse(
        content=pin_set_form(post_url=request.url_for("post_create_pin_set"))
    )


@router.post(path="/pin_set")
def post_create_pin_set(
    request: Request,
    name: str = Form(),
) -> HTMLResponse:
    with session_maker.begin() as session:
        pin_set = PinSet(name=name)

        session.add(instance=pin_set)
        session.flush()
        pin_set_id = pin_set.id

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_pin_set", id=pin_set_id))}
    )
