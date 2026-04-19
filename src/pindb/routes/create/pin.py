from datetime import date
from typing import Annotated, Sequence
from uuid import UUID

from fastapi import Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from pydantic import BeforeValidator
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pindb.database import Artist, Shop, session_maker
from pindb.database.currency import Currency
from pindb.database.grade import Grade
from pindb.database.link import Link
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.tag import Tag, apply_pin_tags
from pindb.file_handler import save_image
from pindb.log import user_logger
from pindb.model_utils import (
    MagnitudeParseError,
    empty_str_list_to_none,
    empty_str_to_none,
    parse_magnitude_mm,
)
from pindb.models.acquisition_type import AcquisitionType
from pindb.models.funding_type import FundingType
from pindb.search.update import update_pin
from pindb.templates.create_and_edit.pin import pin_form

router = APIRouter()

LOGGER = user_logger("pindb.routes.create.pin")


@router.get(path="/pin")
def get_create_pin(
    request: Request,
    duplicate_from: int | None = Query(default=None),
) -> HTMLResponse:
    with session_maker() as session:
        currencies: Sequence[Currency] = session.scalars(
            statement=select(Currency)
        ).all()

        options_base_url: str = str(
            request.url_for("get_entity_options", entity_type="placeholder")
        ).removesuffix("/placeholder")

        duplicate_source: Pin | None = None
        prefill_shops: list[Shop] = []
        prefill_tags: list[Tag] = []
        prefill_pin_sets: list[PinSet] = []
        prefill_artists: list[Artist] = []
        if duplicate_from is not None:
            duplicate_source = session.scalar(
                select(Pin)
                .where(Pin.id == duplicate_from)
                .options(
                    selectinload(Pin.shops),
                    selectinload(Pin.explicit_tags),
                    selectinload(Pin.artists),
                    selectinload(Pin.sets),
                    selectinload(Pin.links),
                    selectinload(Pin.grades),
                    selectinload(Pin.currency),
                )
            )
            if duplicate_source is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Pin {duplicate_from} not found to duplicate.",
                )
            prefill_shops = list(duplicate_source.shops)
            prefill_tags = list(duplicate_source.explicit_tags)
            prefill_pin_sets = list(duplicate_source.sets)
            prefill_artists = list(duplicate_source.artists)

        return HTMLResponse(
            content=pin_form(
                post_url=request.url_for("post_create_pin"),
                shops=prefill_shops,
                pin_sets=prefill_pin_sets,
                tags=prefill_tags,
                currencies=currencies,
                artists=prefill_artists,
                options_base_url=options_base_url,
                request=request,
                duplicate_source=duplicate_source,
            )
        )


@router.post(path="/pin")
async def post_create_pin(
    request: Request,
    front_image: UploadFile = Form(),
    name: str = Form(),
    acquisition_type: AcquisitionType = Form(),
    grade_names: list[str] = Form(),
    grade_prices: list[str] = Form(),
    currency_id: int = Form(default=999),
    shop_ids: list[int] = Form(default_factory=list),
    tag_ids: list[int] = Form(default_factory=list),
    pin_sets_ids: list[int] = Form(default_factory=list),
    artist_ids: list[int] = Form(default_factory=list),
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
    LOGGER.info("Creating pin name=%r shops=%s artists=%s", name, shop_ids, artist_ids)

    try:
        width_mm = parse_magnitude_mm(field_label="Width", raw=width)
        height_mm = parse_magnitude_mm(field_label="Height", raw=height)
    except MagnitudeParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    back_image_guid: UUID | None = None
    front_image_guid: UUID = await save_image(file=front_image)

    if back_image:
        back_image_guid: UUID = await save_image(file=back_image)

    with session_maker.begin() as session:
        pin_shops: set[Shop] = set(
            session.scalars(
                statement=select(Shop).where(Shop.id.in_(other=shop_ids))
            ).all()
        )
        pin_sets: set[PinSet] = set(
            session.scalars(
                statement=select(PinSet).where(PinSet.id.in_(other=pin_sets_ids))
            ).all()
        )
        pin_artists: set[Artist] = set(
            session.scalars(
                statement=select(Artist).where(Artist.id.in_(other=artist_ids))
            ).all()
        )
        currency: Currency = session.get_one(entity=Currency, ident=currency_id)
        new_links: set[Link] = (
            {Link(path=link) for link in links} if links else set[Link]()
        )
        new_grades: set[Grade] = {
            Grade(name=grade_name, price=float(p) if (p := price_str.strip()) else None)
            for grade_name, price_str in zip(grade_names, grade_prices)
            if grade_name.strip()
        }

        new_pin = Pin(
            name=name,
            acquisition_type=acquisition_type,
            front_image_guid=front_image_guid,
            grades=new_grades,
            currency=currency,
            shops=pin_shops,
            limited_edition=limited_edition,
            number_produced=number_produced,
            release_date=release_date,
            end_date=end_date,
            funding_type=funding_type,
            posts=posts,
            width=width_mm,
            height=height_mm,
            back_image_guid=back_image_guid,
            description=None,
            artists=pin_artists,
            sets=pin_sets,
            links=new_links,
        )

        session.add(instance=new_pin)
        session.flush()
        apply_pin_tags(new_pin.id, tag_ids, session)
        pin_id: int = new_pin.id

    with session_maker() as session:
        created_pin: Pin | None = session.scalar(
            select(Pin)
            .where(Pin.id == pin_id)
            .options(
                selectinload(Pin.shops).selectinload(Shop.aliases),
                selectinload(Pin.tags),
                selectinload(Pin.artists).selectinload(Artist.aliases),
            )
        )
    if created_pin is not None:
        update_pin(pin=created_pin)

    LOGGER.info("Created pin id=%d name=%r", pin_id, name)

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
