"""
FastAPI routes: `routes/list/tags.py`.
"""

from typing import Annotated, Sequence

from fastapi import Query, Request
from fastapi.routing import APIRouter
from htpy.starlette import HtpyResponse
from pydantic import BeforeValidator
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from pindb.database import async_session_maker
from pindb.database.joins import pins_tags
from pindb.database.tag import Tag, TagCategory
from pindb.model_utils import empty_str_to_none
from pindb.models.list_view import EntityListView
from pindb.models.sort_order import SortOrder
from pindb.search.search import search_tags
from pindb.templates.list.base import DEFAULT_PER_PAGE
from pindb.templates.list.tags import tags_list, tags_list_section

router = APIRouter()


@router.get(path="/tags")
async def get_list_tags(
    request: Request,
    page: int = Query(default=1, ge=1),
    view: EntityListView = Query(default=EntityListView.grid),
    q: str = Query(default=""),
    category: Annotated[
        TagCategory | None,
        Query(),
        BeforeValidator(empty_str_to_none),
    ] = None,
    sort: SortOrder = Query(default=SortOrder.name),
) -> HtpyResponse:
    offset: int = (page - 1) * DEFAULT_PER_PAGE
    base_url: str = str(request.url_for("get_list_tags"))

    if sort == SortOrder.newest:
        order_parts = (Tag.created_at.desc(),)
    elif sort == SortOrder.oldest:
        order_parts = (Tag.created_at.asc(),)
    else:
        pin_count_sq = (
            select(func.count())
            .select_from(pins_tags)
            .where(pins_tags.c.tag_id == Tag.id)
        ).scalar_subquery()
        order_parts = ((pin_count_sq == 0).asc(), Tag.name.asc())

    async with async_session_maker() as session:
        if q:
            tags_list_result, total_count = await search_tags(
                query=q,
                session=session,
                category=category,
                offset=offset,
                limit=DEFAULT_PER_PAGE,
            )
            tags: Sequence[Tag] = tags_list_result
        else:
            total_count = await session.scalar(select(func.count(Tag.id))) or 0
            stmt = select(Tag).options(selectinload(Tag.pins)).order_by(*order_parts)
            if category:
                stmt = stmt.where(Tag.category == category)
            tags = (
                await session.scalars(stmt.limit(DEFAULT_PER_PAGE).offset(offset))
            ).all()

        if request.headers.get("HX-Request"):
            return HtpyResponse(
                tags_list_section(
                    request=request,
                    tags=tags,
                    view=view,
                    page=page,
                    total_count=total_count,
                    base_url=base_url,
                    q=q,
                    category=category,
                    sort=sort,
                )
            )
        return HtpyResponse(
            tags_list(
                request=request,
                tags=tags,
                view=view,
                page=page,
                total_count=total_count,
                base_url=base_url,
                q=q,
                category=category,
                sort=sort,
            )
        )
