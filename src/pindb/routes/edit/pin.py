"""
FastAPI routes: `routes/edit/pin.py`.
"""

from typing import Sequence
from uuid import UUID

from fastapi import Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from htpy.starlette import HtpyResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pindb.auth import EditorUser
from pindb.database import async_session_maker
from pindb.database.currency import Currency
from pindb.database.entity_type import EntityType
from pindb.database.pending_edit_utils import (
    apply_snapshot_in_memory,
    get_edit_chain,
    get_effective_snapshot,
)
from pindb.database.pin import Pin
from pindb.database.pin_writes import sync_symmetric_pin_links, upsert_grades
from pindb.database.tag import apply_pin_tags
from pindb.file_handler import save_image
from pindb.htmx_toast import htmx_error_toast, hx_redirect_with_toast_headers
from pindb.log import user_logger
from pindb.model_utils import MagnitudeParseError, parse_magnitude_mm
from pindb.routes._guards import assert_editor_can_edit, needs_pending_edit
from pindb.routes._pin_shared import (
    PinFormParams,
    load_pin_links,
    load_pin_relations,
    parse_grade_dicts,
)
from pindb.routes._urls import slugify_for_url
from pindb.routes.edit._pending_helpers import replace_links, submit_pending_edit
from pindb.search.update import sync_entity
from pindb.templates.create_and_edit.pin import pin_form

router = APIRouter()

LOGGER = user_logger("pindb.routes.edit.pin")


_PIN_SELECTINLOADS = (
    selectinload(Pin.shops),
    selectinload(Pin.tags),
    selectinload(Pin.explicit_tags),
    selectinload(Pin.artists),
    selectinload(Pin.sets),
    selectinload(Pin.links),
    selectinload(Pin.grades),
    selectinload(Pin.currency),
    selectinload(Pin.variants),
    selectinload(Pin.unauthorized_copies),
)


@router.get(path="/pin/{id}", response_model=None)
async def get_edit_pin(
    request: Request,
    id: int,
    current_user: EditorUser,
) -> HtpyResponse:
    async with async_session_maker() as session:
        pin: Pin | None = await session.scalar(
            select(Pin).where(Pin.id == id).options(*_PIN_SELECTINLOADS)
        )

        if pin is None:
            raise HTTPException(status_code=404, detail="Pin not found")

        assert_editor_can_edit(pin, current_user)

        if needs_pending_edit(pin, current_user):
            chain = await get_edit_chain(session, "pins", id)
            if chain:
                effective = get_effective_snapshot(pin, chain)
                with session.no_autoflush:
                    await apply_snapshot_in_memory(pin, effective, session)

        currencies: Sequence[Currency] = (
            await session.scalars(statement=select(Currency))
        ).all()

        options_base_url: str = str(
            request.url_for("get_entity_options", entity_type="placeholder")
        ).removesuffix("/placeholder")

        return HtpyResponse(
            pin_form(
                post_url=request.url_for("post_edit_pin", id=id),
                shops=list(pin.shops),
                tags=list(pin.explicit_tags),
                pin_sets=list(pin.sets),
                pin=pin,
                currencies=currencies,
                artists=list(pin.artists),
                variant_pins=list(pin.variants),
                unauthorized_copy_pins=list(pin.unauthorized_copies),
                options_base_url=options_base_url,
                request=request,
            )
        )


@router.post(path="/pin/{id}", response_model=None)
async def post_edit_pin(
    request: Request,
    id: int,
    current_user: EditorUser,
    front_image: UploadFile | None = Form(default=None),
    fields: PinFormParams = Depends(),
    back_image: UploadFile | None = Form(default=None),
) -> HTMLResponse:
    try:
        width_mm = parse_magnitude_mm(field_label="Width", raw=fields.width)
        height_mm = parse_magnitude_mm(field_label="Height", raw=fields.height)
    except MagnitudeParseError as exc:
        if request.headers.get("HX-Request"):
            return htmx_error_toast(message=str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    back_image_guid: UUID | None = None
    front_image_guid: UUID | None = None

    if front_image:
        front_image_guid = await save_image(file=front_image)
    if back_image:
        back_image_guid = await save_image(file=back_image)

    async with async_session_maker.begin() as session:
        pin: Pin | None = await session.scalar(
            select(Pin).where(Pin.id == id).options(*_PIN_SELECTINLOADS)
        )
        if not pin:
            raise HTTPException(status_code=404, detail="Pin not found")

        assert_editor_can_edit(pin, current_user)

        if needs_pending_edit(pin, current_user):
            LOGGER.info(
                "Submitting pending edit for pin id=%d name=%r", id, fields.name
            )
            chain = await get_edit_chain(session, "pins", id)
            old_snapshot: dict[str, object] = get_effective_snapshot(pin, chain)

            grades_list = parse_grade_dicts(fields.grade_names, fields.grade_prices)
            grades_list.sort(key=lambda grade: grade["name"])  # type: ignore[arg-type, return-value]

            return await submit_pending_edit(
                session=session,
                entity=pin,
                entity_table="pins",
                entity_id=id,
                field_updates={
                    "name": fields.name,
                    "description": fields.description,
                    "acquisition_type": fields.acquisition_type.value,
                    "limited_edition": fields.limited_edition,
                    "number_produced": fields.number_produced,
                    "release_date": fields.release_date.isoformat()
                    if fields.release_date
                    else None,
                    "end_date": fields.end_date.isoformat()
                    if fields.end_date
                    else None,
                    "funding_type": fields.funding_type.value
                    if fields.funding_type
                    else None,
                    "posts": fields.posts,
                    "width": width_mm,
                    "height": height_mm,
                    "currency_id": fields.currency_id,
                    "front_image_guid": str(front_image_guid)
                    if front_image_guid
                    else old_snapshot["front_image_guid"],
                    "back_image_guid": str(back_image_guid)
                    if back_image_guid
                    else old_snapshot["back_image_guid"],
                    "shop_ids": sorted(fields.shop_ids),
                    "tag_ids": sorted(fields.tag_ids),
                    "artist_ids": sorted(fields.artist_ids),
                    "pin_set_ids": sorted(fields.pin_sets_ids),
                    "variant_pin_ids": sorted(
                        pid for pid in fields.variant_pin_ids if pid != id
                    ),
                    "unauthorized_copy_pin_ids": sorted(
                        pid for pid in fields.unauthorized_copy_pin_ids if pid != id
                    ),
                    "links": sorted(fields.links or []),
                    "grades": grades_list,
                },
                current_user=current_user,
                request=request,
                redirect_route="get_pin",
            )

        # Direct edit — admin, or editor on their own pending-new entry.
        LOGGER.info("Editing pin id=%d name=%r", id, fields.name)
        pin_shops, pin_sets, pin_artists = await load_pin_relations(
            session=session,
            shop_ids=fields.shop_ids,
            pin_sets_ids=fields.pin_sets_ids,
            artist_ids=fields.artist_ids,
        )
        variant_pins, unauthorized_copy_pins = await load_pin_links(
            session=session,
            self_pin_id=id,
            variant_pin_ids=fields.variant_pin_ids,
            unauthorized_copy_pin_ids=fields.unauthorized_copy_pin_ids,
        )
        currency: Currency = await session.get_one(
            entity=Currency, ident=fields.currency_id
        )

        pin.name = fields.name
        pin.description = fields.description
        pin.acquisition_type = fields.acquisition_type
        pin.currency = currency
        if front_image_guid:
            pin.front_image_guid = front_image_guid
        pin.shops = pin_shops
        pin.sets = pin_sets
        pin.artists = pin_artists
        pin.limited_edition = fields.limited_edition
        pin.number_produced = fields.number_produced
        pin.release_date = fields.release_date
        pin.end_date = fields.end_date
        pin.funding_type = fields.funding_type
        pin.posts = fields.posts
        pin.width = width_mm
        pin.height = height_mm
        if back_image_guid:
            pin.back_image_guid = back_image_guid

        await replace_links(entity=pin, urls=fields.links, session=session)

        await upsert_grades(
            pin=pin,
            grades=parse_grade_dicts(fields.grade_names, fields.grade_prices),
            session=session,
        )

        await apply_pin_tags(pin.id, fields.tag_ids, session)
        sync_symmetric_pin_links(
            pin=pin,
            variants=variant_pins,
            unauthorized_copies=unauthorized_copy_pins,
        )
        await session.flush()
        pin_id: int = pin.id

    await sync_entity(EntityType.pin, pin_id)

    return HTMLResponse(
        headers=hx_redirect_with_toast_headers(
            redirect_url=str(
                request.url_for(
                    "get_pin",
                    slug=slugify_for_url(name=fields.name, fallback="pin"),
                    id=pin_id,
                )
            ),
            message="Pin updated.",
        )
    )
