"""
FastAPI routes: `routes/create/pin.py`.
"""

from typing import Sequence
from uuid import UUID

from fastapi import Depends, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pindb.database import Artist, Shop, session_maker
from pindb.database.currency import Currency
from pindb.database.grade import Grade
from pindb.database.link import Link
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.pin_writes import sync_symmetric_pin_links
from pindb.database.tag import Tag, apply_pin_tags
from pindb.file_handler import save_image
from pindb.htmx_toast import hx_redirect_with_toast_headers
from pindb.log import user_logger
from pindb.model_utils import MagnitudeParseError, parse_magnitude_mm
from pindb.routes._pin_shared import (
    PinFormParams,
    load_pin_links,
    load_pin_relations,
)
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
        prefill_variants: list[Pin] = []
        prefill_copies: list[Pin] = []
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
                    selectinload(Pin.variants),
                    selectinload(Pin.unauthorized_copies),
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
            prefill_variants = list(duplicate_source.variants)
            prefill_copies = list(duplicate_source.unauthorized_copies)

        return HTMLResponse(
            content=pin_form(
                post_url=request.url_for("post_create_pin"),
                shops=prefill_shops,
                pin_sets=prefill_pin_sets,
                tags=prefill_tags,
                currencies=currencies,
                artists=prefill_artists,
                variant_pins=prefill_variants,
                unauthorized_copy_pins=prefill_copies,
                options_base_url=options_base_url,
                request=request,
                duplicate_source=duplicate_source,
            )
        )


@router.post(path="/pin")
async def post_create_pin(
    request: Request,
    front_image: UploadFile = Form(),
    fields: PinFormParams = Depends(),
    back_image: UploadFile | None = Form(default=None),
) -> HTMLResponse:
    LOGGER.info(
        "Creating pin name=%r shops=%s artists=%s",
        fields.name,
        fields.shop_ids,
        fields.artist_ids,
    )

    try:
        width_mm = parse_magnitude_mm(field_label="Width", raw=fields.width)
        height_mm = parse_magnitude_mm(field_label="Height", raw=fields.height)
    except MagnitudeParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    back_image_guid: UUID | None = None
    front_image_guid: UUID = await save_image(file=front_image)

    if back_image:
        back_image_guid = await save_image(file=back_image)

    with session_maker.begin() as session:
        pin_shops, pin_sets, pin_artists = load_pin_relations(
            session=session,
            shop_ids=fields.shop_ids,
            pin_sets_ids=fields.pin_sets_ids,
            artist_ids=fields.artist_ids,
        )
        variant_pins, unauthorized_copy_pins = load_pin_links(
            session=session,
            self_pin_id=None,
            variant_pin_ids=fields.variant_pin_ids,
            unauthorized_copy_pin_ids=fields.unauthorized_copy_pin_ids,
        )
        currency: Currency = session.get_one(entity=Currency, ident=fields.currency_id)
        new_links: set[Link] = (
            {Link(path=link) for link in fields.links} if fields.links else set[Link]()
        )
        new_grades: set[Grade] = {
            Grade(name=grade_name, price=float(p) if (p := price_str.strip()) else None)
            for grade_name, price_str in zip(fields.grade_names, fields.grade_prices)
            if grade_name.strip()
        }

        new_pin = Pin(
            name=fields.name,
            acquisition_type=fields.acquisition_type,
            front_image_guid=front_image_guid,
            grades=new_grades,
            currency=currency,
            shops=pin_shops,
            limited_edition=fields.limited_edition,
            number_produced=fields.number_produced,
            release_date=fields.release_date,
            end_date=fields.end_date,
            funding_type=fields.funding_type,
            posts=fields.posts,
            width=width_mm,
            height=height_mm,
            back_image_guid=back_image_guid,
            description=fields.description,
            artists=pin_artists,
            sets=pin_sets,
            links=new_links,
        )

        session.add(instance=new_pin)
        session.flush()
        apply_pin_tags(new_pin.id, fields.tag_ids, session)
        sync_symmetric_pin_links(
            pin=new_pin,
            variants=variant_pins,
            unauthorized_copies=unauthorized_copy_pins,
        )
        pin_id: int = new_pin.id

    with session_maker() as session:
        created_pin: Pin | None = session.scalar(
            select(Pin)
            .where(Pin.id == pin_id)
            .options(
                selectinload(Pin.shops).selectinload(Shop.aliases),
                selectinload(Pin.tags).selectinload(Tag.aliases),
                selectinload(Pin.artists).selectinload(Artist.aliases),
            )
        )
    if created_pin is not None:
        update_pin(pin=created_pin)

    LOGGER.info("Created pin id=%d name=%r", pin_id, fields.name)

    return HTMLResponse(
        headers=hx_redirect_with_toast_headers(
            redirect_url=str(request.url_for("get_pin", id=pin_id)),
            message="Pin created.",
        )
    )
