"""
FastAPI routes: `routes/list/pin_sets.py`.
"""

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
from pindb.search.search import search_pin_sets
from pindb.templates.list.base import DEFAULT_PER_PAGE
from pindb.templates.list.pin_sets import pin_sets_list, pin_sets_list_section

router = APIRouter()


@router.get(path="/pin_sets")
def get_list_pin_sets(
    request: Request,
    page: int = Query(default=1, ge=1),
    view: EntityListView = Query(default=EntityListView.grid),
    q: str = Query(default=""),
) -> HTMLResponse:
    offset: int = (page - 1) * DEFAULT_PER_PAGE
    base_url: str = str(request.url_for("get_list_pin_sets"))

    with session_maker() as session:
        if q:
            all_results, total_count = search_pin_sets(
                query=q,
                session=session,
                offset=offset,
                limit=DEFAULT_PER_PAGE,
            )
            # List page shows global sets only — filter after fetch
            pin_sets: Sequence[PinSet] = [
                ps for ps in all_results if ps.owner_id is None
            ]
            total_count = len(pin_sets)
        else:
            total_count = (
                session.scalar(
                    select(func.count(PinSet.id))
                    .outerjoin(User, PinSet.owner_id == User.id)
                    .where(PinSet.owner_id.is_(None))
                )
                or 0
            )
            pin_sets = session.scalars(
                select(PinSet)
                .outerjoin(User, PinSet.owner_id == User.id)
                .where(PinSet.owner_id.is_(None))
                .options(selectinload(PinSet.pins))
                .order_by(PinSet.name.asc())
                .limit(DEFAULT_PER_PAGE)
                .offset(offset)
            ).all()

        if request.headers.get("HX-Request"):
            return HTMLResponse(
                content=pin_sets_list_section(
                    request=request,
                    pin_sets=pin_sets,
                    view=view,
                    page=page,
                    total_count=total_count,
                    base_url=base_url,
                    q=q,
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
                q=q,
            )
        )
