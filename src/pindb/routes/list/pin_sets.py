"""
FastAPI routes: `routes/list/pin_sets.py`.
"""

from typing import Sequence

from fastapi import Query, Request
from fastapi.routing import APIRouter
from htpy.starlette import HtpyResponse
from sqlalchemy import func, select

from pindb.database import async_session_maker
from pindb.database.joins import pin_set_memberships
from pindb.database.pin_previews import PinPreviews, load_pin_previews
from pindb.database.pin_set import PinSet
from pindb.database.user import User
from pindb.models.list_view import EntityListView
from pindb.models.sort_order import SortOrder
from pindb.routes.list._render import list_response
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
            # List page shows global sets only; filter in Meili so offset/limit
            # and total_count stay correct across pages.
            pin_sets: Sequence[PinSet]
            pin_sets, total_count = await search_pin_sets(
                query=q,
                session=session,
                offset=offset,
                limit=DEFAULT_PER_PAGE,
                global_only=True,
            )
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
                    .order_by(order_by)
                    .limit(DEFAULT_PER_PAGE)
                    .offset(offset)
                )
            ).all()

        previews: PinPreviews = await load_pin_previews(
            session,
            join_table=pin_set_memberships,
            entity_column=pin_set_memberships.c.set_id,
            entity_ids=[pin_set.id for pin_set in pin_sets],
        )

        return list_response(
            request,
            full=pin_sets_list,
            section=pin_sets_list_section,
            pin_sets=pin_sets,
            previews=previews,
            view=view,
            page=page,
            total_count=total_count,
            base_url=base_url,
            q=q,
            sort=sort,
        )
