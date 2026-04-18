from datetime import date
from typing import Annotated, Sequence
from uuid import UUID

from fastapi import Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from pydantic import BeforeValidator
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pindb.auth import EditorUser
from pindb.database import Artist, Shop, session_maker
from pindb.database.currency import Currency
from pindb.database.pending_edit_utils import (
    apply_snapshot_in_memory,
    get_edit_chain,
    get_effective_snapshot,
)
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.pin_writes import upsert_grades
from pindb.database.tag import apply_pin_tags
from pindb.file_handler import save_image
from pindb.model_utils import empty_str_list_to_none, empty_str_to_none, magnitude_to_mm
from pindb.models.acquisition_type import AcquisitionType
from pindb.models.funding_type import FundingType
from pindb.routes._guards import assert_editor_can_edit, needs_pending_edit
from pindb.routes.edit._pending_helpers import replace_links, submit_pending_edit
from pindb.templates.create_and_edit.pin import pin_form

router = APIRouter()


_PIN_SELECTINLOADS = (
    selectinload(Pin.shops),
    selectinload(Pin.tags),
    selectinload(Pin.explicit_tags),
    selectinload(Pin.artists),
    selectinload(Pin.sets),
    selectinload(Pin.links),
    selectinload(Pin.grades),
    selectinload(Pin.currency),
)


@router.get(path="/pin/{id}", response_model=None)
def get_edit_pin(
    request: Request,
    id: int,
    current_user: EditorUser,
) -> HTMLResponse:
    with session_maker() as session:
        pin: Pin | None = session.scalar(
            select(Pin).where(Pin.id == id).options(*_PIN_SELECTINLOADS)
        )

        if pin is None:
            raise HTTPException(status_code=404, detail="Pin not found")

        assert_editor_can_edit(pin, current_user)

        if needs_pending_edit(pin, current_user):
            chain = get_edit_chain(session, "pins", id)
            if chain:
                effective = get_effective_snapshot(pin, chain)
                with session.no_autoflush:
                    apply_snapshot_in_memory(pin, effective, session)

        currencies: Sequence[Currency] = session.scalars(
            statement=select(Currency)
        ).all()

        options_base_url: str = str(
            request.url_for("get_entity_options", entity_type="placeholder")
        ).removesuffix("/placeholder")

        return HTMLResponse(
            content=pin_form(
                post_url=request.url_for("post_edit_pin", id=id),
                shops=list(pin.shops),
                tags=list(pin.explicit_tags),
                pin_sets=list(pin.sets),
                pin=pin,
                currencies=currencies,
                artists=list(pin.artists),
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
    back_image_guid: UUID | None = None
    front_image_guid: UUID | None = None

    if front_image:
        front_image_guid = await save_image(file=front_image)
    if back_image:
        back_image_guid = await save_image(file=back_image)

    width_mm: float | None = magnitude_to_mm(magnitude=width) if width else None
    height_mm: float | None = magnitude_to_mm(magnitude=height) if height else None

    with session_maker.begin() as session:
        pin: Pin | None = session.scalar(
            select(Pin).where(Pin.id == id).options(*_PIN_SELECTINLOADS)
        )
        if not pin:
            raise HTTPException(status_code=404, detail="Pin not found")

        assert_editor_can_edit(pin, current_user)

        if needs_pending_edit(pin, current_user):
            chain = get_edit_chain(session, "pins", id)
            old_snapshot: dict[str, object] = get_effective_snapshot(pin, chain)

            grades_list: list[dict[str, object]] = []
            for grade_name, price_str in zip(grade_names, grade_prices):
                if not grade_name.strip():
                    continue
                stripped_price = price_str.strip()
                grades_list.append(
                    {
                        "name": grade_name,
                        "price": float(stripped_price) if stripped_price else None,
                    }
                )
            grades_list.sort(key=lambda grade: grade["name"])  # type: ignore[arg-type, return-value]

            return submit_pending_edit(
                session=session,
                entity=pin,
                entity_table="pins",
                entity_id=id,
                field_updates={
                    "name": name,
                    "acquisition_type": acquisition_type.value,
                    "limited_edition": limited_edition,
                    "number_produced": number_produced,
                    "release_date": release_date.isoformat() if release_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "funding_type": funding_type.value if funding_type else None,
                    "posts": posts,
                    "width": width_mm,
                    "height": height_mm,
                    "currency_id": currency_id,
                    "front_image_guid": str(front_image_guid)
                    if front_image_guid
                    else old_snapshot["front_image_guid"],
                    "back_image_guid": str(back_image_guid)
                    if back_image_guid
                    else old_snapshot["back_image_guid"],
                    "shop_ids": sorted(shop_ids),
                    "tag_ids": sorted(tag_ids),
                    "artist_ids": sorted(artist_ids),
                    "pin_set_ids": sorted(pin_sets_ids),
                    "links": sorted(links or []),
                    "grades": grades_list,
                },
                current_user=current_user,
                request=request,
                redirect_route="get_pin",
            )

        # Direct edit — admin, or editor on their own pending-new entry.
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

        pin.name = name
        pin.acquisition_type = acquisition_type
        pin.currency = currency
        if front_image_guid:
            pin.front_image_guid = front_image_guid
        pin.shops = pin_shops
        pin.sets = pin_sets
        pin.artists = pin_artists
        pin.limited_edition = limited_edition
        pin.number_produced = number_produced
        pin.release_date = release_date
        pin.end_date = end_date
        pin.funding_type = funding_type
        pin.posts = posts
        pin.width = width_mm
        pin.height = height_mm
        if back_image_guid:
            pin.back_image_guid = back_image_guid

        replace_links(entity=pin, urls=links, session=session)

        parsed_grades: list[dict[str, object]] = []
        for grade_name, price_str in zip(grade_names, grade_prices):
            if not grade_name.strip():
                continue
            stripped_price = price_str.strip()
            parsed_grades.append(
                {
                    "name": grade_name,
                    "price": float(stripped_price) if stripped_price else None,
                }
            )

        upsert_grades(pin=pin, grades=parsed_grades, session=session)

        apply_pin_tags(pin.id, tag_ids, session)
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
