"""
FastAPI routes: `routes/list/tags.py`.
"""

from typing import Annotated, Sequence

from fastapi import Query, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from pydantic import BeforeValidator
from sqlalchemy import exists, func, select

from pindb.database import async_session_maker
from pindb.database.joins import pins_tags
from pindb.database.pin_previews import PinPreviews, load_pin_previews
from pindb.database.tag import Tag, TagCategory
from pindb.model_utils import empty_str_to_none
from pindb.models.list_view import EntityListView
from pindb.models.sort_order import SortOrder
from pindb.routes.list._render import list_response
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
) -> HTMLResponse:
    offset: int = (page - 1) * DEFAULT_PER_PAGE
    base_url: str = str(request.url_for("get_list_tags"))

    if sort == SortOrder.newest:
        order_parts = (Tag.created_at.desc(),)
    elif sort == SortOrder.oldest:
        order_parts = (Tag.created_at.asc(),)
    else:
        # Tags with pins sort ahead of empty ones. Whether the tag has *any* pin is
        # all that matters, so EXISTS (an index probe on ix_pins_tags_tag_id that
        # stops at the first hit) answers it — the COUNT subquery this replaces had
        # to tally every row of every tag before the LIMIT could be applied.
        has_pins = exists().where(pins_tags.c.tag_id == Tag.id)
        order_parts = (has_pins.desc(), Tag.name.asc())

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
            count_stmt = select(func.count(Tag.id))
            stmt = select(Tag).order_by(*order_parts)
            if category:
                count_stmt = count_stmt.where(Tag.category == category)
                stmt = stmt.where(Tag.category == category)
            total_count = await session.scalar(count_stmt) or 0
            tags = (
                await session.scalars(stmt.limit(DEFAULT_PER_PAGE).offset(offset))
            ).all()

        previews: PinPreviews = await load_pin_previews(
            session,
            join_table=pins_tags,
            entity_column=pins_tags.c.tag_id,
            entity_ids=[tag.id for tag in tags],
        )

        return list_response(
            request,
            full=tags_list,
            section=tags_list_section,
            tags=tags,
            previews=previews,
            view=view,
            page=page,
            total_count=total_count,
            base_url=base_url,
            q=q,
            category=category,
            sort=sort,
        )
