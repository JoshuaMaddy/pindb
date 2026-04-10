from typing import Sequence

from fastapi import Query, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from pindb.database import Artist, session_maker
from pindb.models.list_view import EntityListView
from pindb.templates.list.artists import artists_list, artists_list_section
from pindb.templates.list.base import DEFAULT_PER_PAGE

router = APIRouter()


@router.get(path="/artists")
def get_list_artists(
    request: Request,
    page: int = Query(default=1, ge=1),
    view: EntityListView = Query(default=EntityListView.grid),
) -> HTMLResponse:
    with session_maker.begin() as session:
        total_count: int = session.scalar(select(func.count(Artist.id))) or 0
        artists: Sequence[Artist] = session.scalars(
            select(Artist)
            .options(selectinload(Artist.pins))
            .order_by(Artist.name.asc())
            .limit(DEFAULT_PER_PAGE)
            .offset((page - 1) * DEFAULT_PER_PAGE)
        ).all()

        base_url: str = str(request.url_for("get_list_artists"))

        if request.headers.get("HX-Request"):
            return HTMLResponse(
                content=artists_list_section(
                    request=request,
                    artists=artists,
                    view=view,
                    page=page,
                    total_count=total_count,
                    base_url=base_url,
                )
            )
        return HTMLResponse(
            content=artists_list(
                request=request,
                artists=artists,
                view=view,
                page=page,
                total_count=total_count,
                base_url=base_url,
            )
        )
