from datetime import date
from typing import Annotated
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
from pindb.templates.create_and_edit.pin import pin_form

router = APIRouter(prefix="/edit")


@router.get("/pin/{id}")
def get_edit_pin(
    request: Request,
    id: int,
) -> HTMLResponse:
    with session_maker.begin() as session:
        materials = session.scalars(select(Material)).all()
        shops = session.scalars(select(Shop)).all()
        tags = session.scalars(select(Tag)).all()
        pin_sets = session.scalars(select(PinSet)).all()
        pin = session.get(Pin, id)
        currencies = session.scalars(select(Currency)).all()

        if pin is None:
            return None

        return HTMLResponse(
            pin_form(
                post_url=request.url_for("post_edit_pin", id=id),
                materials=materials,
                shops=shops,
                tags=tags,
                pin_sets=pin_sets,
                pin=pin,
                currencies=currencies,
            )
        )


@router.post("/pin/{id}")
async def post_edit_pin(
    request: Request,
    id: int,
    front_image: UploadFile | None = Form(default=None),
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
    front_image_guid: UUID | None = None

    if front_image:
        front_image_guid = await save_file(front_image)
    if back_image:
        back_image_guid = await save_file(back_image)

    with session_maker.begin() as session:
        pin = session.get(Pin, id)
        if not pin:
            return None

        pin_materials = set(
            session.scalars(select(Material).where(Material.id.in_(material_ids))).all()
        )
        pin_shops = set(
            session.scalars(select(Shop).where(Shop.id.in_(shop_ids))).all()
        )
        pin_tags = set(session.scalars(select(Tag).where(Tag.id.in_(tag_ids))).all())
        pin_sets = set(
            session.scalars(select(PinSet).where(PinSet.id.in_(pin_sets_ids))).all()
        )
        currency = session.get_one(Currency, currency_id)

        pin_str_links = [link.path for link in pin.links]
        new_links: set[Link] = set()
        for link in links if links else []:
            if link not in pin_str_links:
                new_links.add(Link(path=link))
        new_links.update(pin.links.copy())

        pin.name = name
        pin.acquisition_type = acquisition_type
        pin.original_price = original_price
        pin.currency = currency
        pin.front_image_guid = (
            front_image_guid if front_image_guid else pin.front_image_guid
        )
        pin.materials = pin_materials
        pin.shops = pin_shops
        pin.sets = pin_sets
        pin.tags = pin_tags
        pin.limited_edition = limited_edition
        pin.number_produced = number_produced
        pin.release_date = release_date
        pin.end_date = end_date
        pin.funding_type = funding_type
        pin.posts = posts
        pin.width = magnitude_to_mm(width) if width else width  # type: ignore
        pin.height = magnitude_to_mm(height) if height else height  # type: ignore
        pin.back_image_guid = (
            back_image_guid if back_image_guid else pin.back_image_guid
        )
        pin.links = new_links

        session.flush()
        pin_id = pin.id

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
