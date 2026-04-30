"""
FastAPI routes: `routes/list/pin_sets.py`.
"""

from typing import Sequence

from fastapi import Query, Request
from fastapi.routing import APIRouter
from htpy.starlette import HtpyResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from pindb.database import async_session_maker
from pindb.database.pin_set import PinSet
from pindb.database.user import User
from pindb.models.list_view import EntityListView
from pindb.models.sort_order import SortOrder
from pindb.search.search import search_pin_sets
from pindb.templates.list.base import DEFAULT_PER_PAGE
from pindb.templates.list.pin_sets import pin_sets_list, pin_sets_list_section

router = APIRouter()


@router.get(path="/pin_sets")
async def get_list_pin_sets(
    request: Request,
    page: int = Query(default=1, ge=1),
    view: EntityListView = Query(default=EntityListView.grid),
    q: str = Query(default=""),
    sort: SortOrder = Query(default=SortOrder.name),
) -> HtpyResponse:
    offset: int = (page - 1) * DEFAULT_PER_PAGE
    base_url: str = str(request.url_for("get_list_pin_sets"))

    order_by = (
        PinSet.created_at.desc()
        if sort == SortOrder.newest
        else PinSet.created_at.asc()
        if sort == SortOrder.oldest
        else PinSet.name.asc()
    )

    async with async_session_maker() as session:
        if q:
            all_results, total_count = await search_pin_sets(
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
                await session.scalar(
                    select(func.count(PinSet.id))
                    .outerjoin(User, PinSet.owner_id == User.id)
                    .where(PinSet.owner_id.is_(None))
                )
                or 0
            )
            pin_sets = (
                await session.scalars(
                    select(PinSet)
                    .outerjoin(User, PinSet.owner_id == User.id)
                    .where(PinSet.owner_id.is_(None))
                    .options(selectinload(PinSet.pins))
                    .order_by(order_by)
                    .limit(DEFAULT_PER_PAGE)
                    .offset(offset)
                )
            ).all()

        if request.headers.get("HX-Request"):
            return HtpyResponse(
                pin_sets_list_section(
                    request=request,
                    pin_sets=pin_sets,
                    view=view,
                    page=page,
                    total_count=total_count,
                    base_url=base_url,
                    q=q,
                    sort=sort,
                )
            )
        return HtpyResponse(
            pin_sets_list(
                request=request,
                pin_sets=pin_sets,
                view=view,
                page=page,
                total_count=total_count,
                base_url=base_url,
                q=q,
                sort=sort,
            )
        )
