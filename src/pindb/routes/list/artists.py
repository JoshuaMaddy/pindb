"""
FastAPI routes: `routes/list/artists.py`.
"""

from typing import Sequence

from fastapi import Query, Request
from fastapi.routing import APIRouter
from htpy.starlette import HtpyResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from pindb.database import Artist, async_session_maker
from pindb.models.list_view import EntityListView
from pindb.models.sort_order import SortOrder
from pindb.search.search import search_artists
from pindb.templates.list.artists import artists_list, artists_list_section
from pindb.templates.list.base import DEFAULT_PER_PAGE

router = APIRouter()


@router.get(path="/artists")
async def get_list_artists(
    request: Request,
    page: int = Query(default=1, ge=1),
    view: EntityListView = Query(default=EntityListView.grid),
    q: str = Query(default=""),
    sort: SortOrder = Query(default=SortOrder.name),
) -> HtpyResponse:
    offset: int = (page - 1) * DEFAULT_PER_PAGE
    base_url: str = str(request.url_for("get_list_artists"))

    order_by = (
        Artist.created_at.desc()
        if sort == SortOrder.newest
        else Artist.created_at.asc()
        if sort == SortOrder.oldest
        else Artist.name.asc()
    )

    async with async_session_maker() as session:
        if q:
            artists_result, total_count = await search_artists(
                query=q,
                session=session,
                offset=offset,
                limit=DEFAULT_PER_PAGE,
            )
            artists: Sequence[Artist] = artists_result
        else:
            total_count = await session.scalar(select(func.count(Artist.id))) or 0
            artists = (
                await session.scalars(
                    select(Artist)
                    .options(selectinload(Artist.pins))
                    .order_by(order_by)
                    .limit(DEFAULT_PER_PAGE)
                    .offset(offset)
                )
            ).all()

        if request.headers.get("HX-Request"):
            return HtpyResponse(
                artists_list_section(
                    request=request,
                    artists=artists,
                    view=view,
                    page=page,
                    total_count=total_count,
                    base_url=base_url,
                    q=q,
                    sort=sort,
                )
            )
        return HtpyResponse(
            artists_list(
                request=request,
                artists=artists,
                view=view,
                page=page,
                total_count=total_count,
                base_url=base_url,
                q=q,
                sort=sort,
            )
        )
