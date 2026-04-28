"""
FastAPI routes: `routes/bulk/pin.py`.
"""

from datetime import date
from typing import Sequence, TypeVar
from uuid import UUID, uuid4

from fastapi import Depends, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from htpy.starlette import HtpyResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from pindb.auth import require_admin
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
from pindb.database.tag import apply_pin_tags, normalize_tag_name
from pindb.file_handler import save_image
from pindb.log import user_logger
from pindb.model_utils import parse_magnitude_mm
from pindb.models.acquisition_type import AcquisitionType
from pindb.models.funding_type import FundingType
from pindb.search.update import TAGS_INDEX
from pindb.templates.bulk.pin import bulk_pin_page

LOGGER = user_logger("pindb.routes.bulk.pin")

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
    bulk_id: UUID | None = None,
) -> _NameOnly:
    resolved = normalize_tag_name(name) if model is Tag else name
    entity = session.scalar(select(model).where(model.name == resolved))
    if not entity:
        entity = model(name=resolved)
        session.add(entity)
        session.flush()
        if bulk_id is not None:
            entity.bulk_id = bulk_id  # type: ignore[assignment]
            session.flush()
    return entity


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(path="/options/{entity_type}")
def get_bulk_options(
    entity_type: EntityType,
    q: str = Query(default=""),
    exclude_name: str | None = Query(default=None),
) -> JSONResponse:
    if entity_type == EntityType.tag:
        raw: dict[str, object] = TAGS_INDEX.search(query=q, opt_params={"limit": 50})  # type: ignore[assignment]
        tag_hits: list[dict[str, object]] = raw.get("hits", [])  # type: ignore[assignment]
        return JSONResponse(
            content=[
                {
                    "value": str(hit["name"]),
                    "text": ("(P) " + str(hit.get("display_name") or hit["name"]))
                    if hit.get("is_pending")
                    else str(hit.get("display_name") or hit["name"]),
                    "category": str(hit.get("category", "")),
                }
                for hit in tag_hits
                if exclude_name is None or str(hit.get("name")) != exclude_name
            ]
        )
    model = entity_type.model
    with session_maker() as session:
        rows = session.scalars(
            statement=select(model).where(model.name.ilike(f"%{q}%")).limit(50)
        ).all()
    return JSONResponse(
        content=[
            {"value": row.name, "text": row.name}
            for row in rows
            if exclude_name is None or row.name != exclude_name
        ]
    )


@router.get(path="/pin", dependencies=[Depends(require_admin)])
def get_bulk_pin(request: Request) -> HtpyResponse:
    options_base_url: str = str(
        request.url_for("get_bulk_options", entity_type="placeholder")
    ).removesuffix("/placeholder")

    with session_maker() as session:
        currencies: Sequence[Currency] = session.scalars(
            statement=select(Currency)
        ).all()

        return HtpyResponse(
            bulk_pin_page(
                upload_image_url=str(request.url_for("post_bulk_image")),
                submit_url=str(request.url_for("post_bulk_pins")),
                options_base_url=options_base_url,
                currencies=currencies,
                request=request,
            )
        )


@router.post(path="/pin/image", dependencies=[Depends(require_admin)])
async def post_bulk_image(image: UploadFile = Form()) -> JSONResponse:
    guid: UUID = await save_image(file=image)
    LOGGER.info("Bulk image upload guid=%s", guid)
    return JSONResponse(content={"guid": str(guid)})


@router.post(path="/pin", dependencies=[Depends(require_admin)])
async def post_bulk_pins(body: BulkPinInput) -> JSONResponse:
    results: list[PinRowResult] = []

    # One bulk_id for the entire submission. Admin-created entities auto-approve
    # via audit_events; bulk_id still ties the batch for auditing / grouping.
    bulk_id: UUID = uuid4()
    LOGGER.info("Bulk-creating %d pins bulk_id=%s", len(body.pins), bulk_id)

    with session_maker.begin() as session:
        for index, row in enumerate(body.pins):
            try:
                currency: Currency = session.get_one(
                    entity=Currency, ident=row.currency_id
                )

                shops: set[Shop] = {
                    _get_or_create(
                        session=session, model=Shop, name=name, bulk_id=bulk_id
                    )
                    for name in row.shop_names
                    if name
                }
                explicit_tags: set[Tag] = {
                    _get_or_create(
                        session=session, model=Tag, name=name, bulk_id=bulk_id
                    )
                    for name in row.tag_names
                    if name
                }
                artists: set[Artist] = {
                    _get_or_create(
                        session=session, model=Artist, name=name, bulk_id=bulk_id
                    )
                    for name in row.artist_names
                    if name
                }
                pin_sets: set[PinSet] = {
                    _get_or_create(
                        session=session, model=PinSet, name=name, bulk_id=bulk_id
                    )
                    for name in row.pin_set_names
                    if name
                }

                grades: set[Grade] = {
                    Grade(name=grade.name, price=grade.price) for grade in row.grades
                }
                links: set[Link] = {Link(path=url) for url in row.links if url}

                width_mm = parse_magnitude_mm(field_label="Width", raw=row.width)
                height_mm = parse_magnitude_mm(field_label="Height", raw=row.height)

                new_pin = Pin(
                    name=row.name,
                    acquisition_type=row.acquisition_type,
                    front_image_guid=UUID(row.front_image_guid),
                    back_image_guid=UUID(row.back_image_guid)
                    if row.back_image_guid
                    else None,
                    currency=currency,
                    shops=shops,
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
                    width=width_mm,
                    height=height_mm,
                    description=row.description,
                )

                session.add(new_pin)
                session.flush()
                new_pin.bulk_id = bulk_id
                apply_pin_tags(new_pin.id, {tag.id for tag in explicit_tags}, session)

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

    LOGGER.info(
        "Bulk pin submission complete bulk_id=%s created=%d failed=%d",
        bulk_id,
        created,
        failed,
    )

    return JSONResponse(
        content=BulkPinResult(
            results=results,
            created_count=created,
            failed_count=failed,
        ).model_dump()
    )
