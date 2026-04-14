from typing import Annotated, Sequence

from fastapi import Query, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from pydantic import BeforeValidator
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from pindb.database import session_maker
from pindb.database.tag import Tag, TagCategory
from pindb.model_utils import empty_str_to_none
from pindb.models.list_view import EntityListView
from pindb.search.search import search_tags
from pindb.templates.list.base import DEFAULT_PER_PAGE
from pindb.templates.list.tags import tags_list, tags_list_section

router = APIRouter()


@router.get(path="/tags")
def get_list_tags(
    request: Request,
    page: int = Query(default=1, ge=1),
    view: EntityListView = Query(default=EntityListView.grid),
    q: str = Query(default=""),
    category: Annotated[
        TagCategory | None,
        Query(),
        BeforeValidator(empty_str_to_none),
    ] = None,
) -> HTMLResponse:
    offset: int = (page - 1) * DEFAULT_PER_PAGE
    base_url: str = str(request.url_for("get_list_tags"))

    with session_maker() as session:
        if q:
            tags_list_result, total_count = search_tags(
                query=q,
                session=session,
                category=category,
                offset=offset,
                limit=DEFAULT_PER_PAGE,
            )
            tags: Sequence[Tag] = tags_list_result
        else:
            total_count = session.scalar(select(func.count(Tag.id))) or 0
            stmt = select(Tag).options(selectinload(Tag.pins)).order_by(Tag.name.asc())
            if category:
                stmt = stmt.where(Tag.category == category)
            tags = session.scalars(stmt.limit(DEFAULT_PER_PAGE).offset(offset)).all()

        if request.headers.get("HX-Request"):
            return HTMLResponse(
                content=tags_list_section(
                    request=request,
                    tags=tags,
                    view=view,
                    page=page,
                    total_count=total_count,
                    base_url=base_url,
                    q=q,
                    category=category,
                )
            )
        return HTMLResponse(
            content=tags_list(
                request=request,
                tags=tags,
                view=view,
                page=page,
                total_count=total_count,
                base_url=base_url,
                q=q,
                category=category,
            )
        )
