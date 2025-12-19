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
from pindb.templates.create_and_edit.pin import pin_form

router = APIRouter(prefix="/edit")


@router.get(path="/pin/{id}", response_model=None)
def get_edit_pin(
    request: Request,
    id: int,
) -> HTMLResponse | None:
    with session_maker.begin() as session:
        materials: Sequence[Material] = session.scalars(
            statement=select(Material)
        ).all()
        shops: Sequence[Shop] = session.scalars(statement=select(Shop)).all()
        tags: Sequence[Tag] = session.scalars(statement=select(Tag)).all()
        pin_sets: Sequence[PinSet] = session.scalars(statement=select(PinSet)).all()
        pin: Pin | None = session.get(entity=Pin, ident=id)
        currencies: Sequence[Currency] = session.scalars(
            statement=select(Currency)
        ).all()

        if pin is None:
            return None

        return HTMLResponse(
            content=pin_form(
                post_url=request.url_for("post_edit_pin", id=id),
                materials=materials,
                shops=shops,
                tags=tags,
                pin_sets=pin_sets,
                pin=pin,
                currencies=currencies,
            )
        )


@router.post(path="/pin/{id}", response_model=None)
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
) -> HTMLResponse | None:
    back_image_guid: UUID | None = None
    front_image_guid: UUID | None = None

    if front_image:
        front_image_guid: UUID = await save_file(file=front_image)
    if back_image:
        back_image_guid: UUID = await save_file(file=back_image)

    with session_maker.begin() as session:
        pin: Pin | None = session.get(entity=Pin, ident=id)
        if not pin:
            return None

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

        pin_str_links: list[str] = [link.path for link in pin.links]
        new_links: set[Link] = set()
        for link in links if links else []:
            if link not in pin_str_links:
                new_links.add(Link(path=link))
        new_links.update(pin.links.copy())

        pin.name: str = name
        pin.acquisition_type: AcquisitionType = acquisition_type
        pin.original_price: int | float = original_price
        pin.currency: Currency = currency
        pin.front_image_guid: UUID = (
            front_image_guid if front_image_guid else pin.front_image_guid
        )
        pin.materials: set[Material] = pin_materials
        pin.shops: set[Shop] = pin_shops
        pin.sets: set[PinSet] = pin_sets
        pin.tags: set[Tag] = pin_tags
        pin.limited_edition: bool | None = limited_edition
        pin.number_produced: int | None = number_produced
        pin.release_date: date | None = release_date
        pin.end_date: date | None = end_date
        pin.funding_type: FundingType | None = funding_type
        pin.posts: int = posts
        pin.width: int | float | None = (
            magnitude_to_mm(magnitude=width) if width else width
        )  # type: ignore
        pin.height: int | float | None = (
            magnitude_to_mm(magnitude=height) if height else height
        )  # type: ignore
        pin.back_image_guid: UUID | None = (
            back_image_guid if back_image_guid else pin.back_image_guid
        )
        pin.links: set[Link] = new_links

        session.flush()
        pin_id: int = pin.id

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
