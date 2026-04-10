from typing import Sequence

from fastapi import Query, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from pindb.database import session_maker
from pindb.database.tag import Tag
from pindb.models.list_view import EntityListView
from pindb.templates.list.base import DEFAULT_PER_PAGE
from pindb.templates.list.tags import tags_list, tags_list_section

router = APIRouter()


@router.get(path="/tags")
def get_list_tags(
    request: Request,
    page: int = Query(default=1, ge=1),
    view: EntityListView = Query(default=EntityListView.grid),
) -> HTMLResponse:
    with session_maker.begin() as session:
        total_count: int = session.scalar(select(func.count(Tag.id))) or 0
        tags: Sequence[Tag] = session.scalars(
            select(Tag)
            .options(selectinload(Tag.pins))
            .order_by(Tag.name.asc())
            .limit(DEFAULT_PER_PAGE)
            .offset((page - 1) * DEFAULT_PER_PAGE)
        ).all()

        base_url: str = str(request.url_for("get_list_tags"))

        if request.headers.get("HX-Request"):
            return HTMLResponse(
                content=tags_list_section(
                    request=request,
                    tags=tags,
                    view=view,
                    page=page,
                    total_count=total_count,
                    base_url=base_url,
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
            )
        )
