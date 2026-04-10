from typing import Sequence

from fastapi import Query, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from pindb.database import session_maker
from pindb.database.pin_set import PinSet
from pindb.database.user import User
from pindb.models.list_view import EntityListView
from pindb.templates.list.base import DEFAULT_PER_PAGE
from pindb.templates.list.pin_sets import pin_sets_list, pin_sets_list_section

router = APIRouter()


@router.get(path="/pin_sets")
def get_list_pin_sets(
    request: Request,
    page: int = Query(default=1, ge=1),
    view: EntityListView = Query(default=EntityListView.grid),
) -> HTMLResponse:
    _base_query = (
        select(PinSet)
        .outerjoin(User, PinSet.owner_id == User.id)
        .where(PinSet.owner_id.is_(None))
    )
    with session_maker.begin() as session:
        total_count: int = (
            session.scalar(
                select(func.count(PinSet.id))
                .outerjoin(User, PinSet.owner_id == User.id)
                .where(PinSet.owner_id.is_(None))
            )
            or 0
        )
        pin_sets: Sequence[PinSet] = session.scalars(
            _base_query.options(selectinload(PinSet.pins))
            .order_by(PinSet.name.asc())
            .limit(DEFAULT_PER_PAGE)
            .offset((page - 1) * DEFAULT_PER_PAGE)
        ).all()

        base_url: str = str(request.url_for("get_list_pin_sets"))

        if request.headers.get("HX-Request"):
            return HTMLResponse(
                content=pin_sets_list_section(
                    request=request,
                    pin_sets=pin_sets,
                    view=view,
                    page=page,
                    total_count=total_count,
                    base_url=base_url,
                )
            )
        return HTMLResponse(
            content=pin_sets_list(
                request=request,
                pin_sets=pin_sets,
                view=view,
                page=page,
                total_count=total_count,
                base_url=base_url,
            )
        )
