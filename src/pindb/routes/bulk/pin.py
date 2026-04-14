import logging
from datetime import date
from typing import Sequence, TypeVar
from uuid import UUID

from fastapi import Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.routing import APIRouter
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

LOGGER = logging.getLogger("pindb.routes.bulk.pin")

from pindb.database import (
    Artist,
    PinSet,
    Shop,
    Tag,
    session_maker,
)
from pindb.database.currency import Currency
from pindb.database.entity_type import EntityType
from pindb.database.grade import Grade
from pindb.database.link import Link
from pindb.database.pin import Pin
from pindb.database.tag import resolve_implications
from pindb.file_handler import save_file
from pindb.model_utils import magnitude_to_mm
from pindb.models.acquisition_type import AcquisitionType
from pindb.models.funding_type import FundingType
from pindb.templates.bulk.pin import bulk_pin_page

_NameOnly = TypeVar("_NameOnly", Artist, Tag, Shop, PinSet)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models for JSON submit
# ---------------------------------------------------------------------------


class GradeInput(BaseModel):
    name: str
    price: float | None = None


class PinRowInput(BaseModel):
    name: str
    acquisition_type: AcquisitionType
    front_image_guid: str
    back_image_guid: str | None = None
    currency_id: int = 999
    shop_names: list[str] = []
    tag_names: list[str] = []
    artist_names: list[str] = []
    pin_set_names: list[str] = []
    grades: list[GradeInput] = []
    links: list[str] = []
    limited_edition: bool | None = None
    number_produced: int | None = None
    release_date: date | None = None
    end_date: date | None = None
    funding_type: FundingType | None = None
    posts: int = 1
    width: str | None = None
    height: str | None = None
    description: str | None = None


class BulkPinInput(BaseModel):
    pins: list[PinRowInput]


class PinRowResult(BaseModel):
    index: int
    success: bool
    pin_id: int | None = None
    pin_name: str | None = None
    front_image_guid: str | None = None
    error: str | None = None


class BulkPinResult(BaseModel):
    results: list[PinRowResult]
    created_count: int
    failed_count: int


# ---------------------------------------------------------------------------
# Helper: resolve or create an entity by name
# ---------------------------------------------------------------------------


def _get_or_create(
    session: Session,
    model: type[_NameOnly],
    name: str,
) -> _NameOnly:
    obj = session.scalar(select(model).where(model.name == name))
    if not obj:
        obj = model(name=name)
        session.add(obj)
        session.flush()
    return obj


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(path="/options/{entity_type}")
def get_bulk_options(
    entity_type: EntityType,
    q: str = Query(default=""),
) -> JSONResponse:
    model = entity_type.model
    with session_maker() as session:
        rows = session.scalars(
            statement=select(model).where(model.name.ilike(f"%{q}%")).limit(50)
        ).all()
    return JSONResponse(content=[{"value": row.name, "text": row.name} for row in rows])


@router.get(path="/pin")
def get_bulk_pin(request: Request) -> HTMLResponse:
    options_base_url: str = str(
        request.url_for("get_bulk_options", entity_type="placeholder")
    ).removesuffix("/placeholder")

    with session_maker() as session:
        currencies: Sequence[Currency] = session.scalars(
            statement=select(Currency)
        ).all()

        return HTMLResponse(
            content=bulk_pin_page(
                upload_image_url=str(request.url_for("post_bulk_image")),
                submit_url=str(request.url_for("post_bulk_pins")),
                options_base_url=options_base_url,
                currencies=currencies,
                request=request,
            )
        )


@router.post(path="/pin/image")
async def post_bulk_image(image: UploadFile = Form()) -> JSONResponse:
    guid: UUID = await save_file(file=image)
    return JSONResponse(content={"guid": str(guid)})


@router.post(path="/pin")
async def post_bulk_pins(body: BulkPinInput) -> JSONResponse:
    results: list[PinRowResult] = []

    with session_maker.begin() as session:
        for index, row in enumerate(body.pins):
            try:
                currency: Currency = session.get_one(
                    entity=Currency, ident=row.currency_id
                )

                shops: set[Shop] = {
                    _get_or_create(session=session, model=Shop, name=name)
                    for name in row.shop_names
                    if name
                }
                tags: set[Tag] = {
                    _get_or_create(session=session, model=Tag, name=name)
                    for name in row.tag_names
                    if name
                }
                resolved_tags = resolve_implications(tags, session)
                artists: set[Artist] = {
                    _get_or_create(session=session, model=Artist, name=name)
                    for name in row.artist_names
                    if name
                }
                pin_sets: set[PinSet] = {
                    _get_or_create(session=session, model=PinSet, name=name)
                    for name in row.pin_set_names
                    if name
                }

                grades: set[Grade] = {
                    Grade(name=g.name, price=g.price) for g in row.grades
                }
                links: set[Link] = {Link(path=url) for url in row.links if url}

                new_pin = Pin(
                    name=row.name,
                    acquisition_type=row.acquisition_type,
                    front_image_guid=UUID(row.front_image_guid),
                    back_image_guid=UUID(row.back_image_guid)
                    if row.back_image_guid
                    else None,
                    currency=currency,
                    shops=shops,
                    tags=resolved_tags,
                    artists=artists,
                    sets=pin_sets,
                    grades=grades,
                    links=links,
                    limited_edition=row.limited_edition,
                    number_produced=row.number_produced,
                    release_date=row.release_date,
                    end_date=row.end_date,
                    funding_type=row.funding_type,
                    posts=row.posts,
                    width=magnitude_to_mm(magnitude=row.width) if row.width else None,
                    height=magnitude_to_mm(magnitude=row.height)
                    if row.height
                    else None,
                    description=row.description,
                )

                session.add(new_pin)
                session.flush()

                results.append(
                    PinRowResult(
                        index=index,
                        success=True,
                        pin_id=new_pin.id,
                        pin_name=new_pin.name,
                        front_image_guid=str(new_pin.front_image_guid),
                    )
                )
            except Exception as error:
                LOGGER.error(
                    "row[%d] %r failed: %s", index, row.name, error, exc_info=True
                )
                results.append(
                    PinRowResult(
                        index=index,
                        success=False,
                        error=str(error),
                    )
                )

    created = sum(1 for result in results if result.success)
    failed = sum(1 for result in results if not result.success)

    return JSONResponse(
        content=BulkPinResult(
            results=results,
            created_count=created,
            failed_count=failed,
        ).model_dump()
    )
