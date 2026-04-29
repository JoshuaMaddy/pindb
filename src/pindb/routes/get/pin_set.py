"""
FastAPI routes: `routes/get/pin_set.py`.
"""

from typing import Sequence

from fastapi import Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter
from sqlalchemy import func, select

from pindb.database import Pin, session_maker
from pindb.database.joins import pin_set_memberships
from pindb.database.pin_set import PinSet
from pindb.routes._urls import canonical_slug_redirect, pin_set_url, slugify_for_url
from pindb.templates.components.pins.paginated_pin_grid import (
    _SECTION_ID,
    paginated_pin_grid,
)
from pindb.templates.get.pin_set import pin_set_page

router = APIRouter()


@router.get(path="/pin_set/{slug}/{id}", response_model=None, name="get_pin_set")
@router.get(
    path="/pin_set/{id}",
    response_model=None,
    name="get_pin_set_by_id",
    include_in_schema=False,
)
def get_pin_set(
    request: Request,
    id: int,
    slug: str | None = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=100, ge=10, le=100),
) -> HTMLResponse | RedirectResponse:
    with session_maker() as session:
        pin_set_obj: PinSet | None = session.get(entity=PinSet, ident=id)

        if not pin_set_obj:
            return RedirectResponse(url="/")

        canonical_slug: str = slugify_for_url(name=pin_set_obj.name, fallback="pin_set")
        if slug != canonical_slug:
            return canonical_slug_redirect(
                request=request,
                route_name="get_pin_set",
                canonical_slug=canonical_slug,
                id=id,
            )

        offset: int = (page - 1) * per_page

        total_count: int = (
            session.scalar(
                select(func.count(Pin.id))
                .join(pin_set_memberships, Pin.id == pin_set_memberships.c.pin_id)
                .where(pin_set_memberships.c.set_id == id)
            )
            or 0
        )

        pins: Sequence[Pin] = session.scalars(
            select(Pin)
            .join(pin_set_memberships, Pin.id == pin_set_memberships.c.pin_id)
            .where(pin_set_memberships.c.set_id == id)
            .order_by(pin_set_memberships.c.position.asc())
            .limit(per_page)
            .offset(offset)
        ).all()

        if request.headers.get("HX-Target") == _SECTION_ID:
            return HTMLResponse(
                content=str(
                    paginated_pin_grid(
                        request=request,
                        pins=pins,
                        total_count=total_count,
                        page=page,
                        page_url=str(pin_set_url(request=request, pin_set=pin_set_obj)),
                        per_page=per_page,
                    )
                )
            )

        return HTMLResponse(
            content=str(
                pin_set_page(
                    request=request,
                    pin_set=pin_set_obj,
                    pins=pins,
                    total_count=total_count,
                    page=page,
                    per_page=per_page,
                )
            )
        )
