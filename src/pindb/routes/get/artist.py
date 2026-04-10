from typing import Sequence

from fastapi import Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter
from sqlalchemy import func, select

from pindb.database import Artist, Pin, session_maker
from pindb.database.joins import pins_artists
from pindb.templates.components.paginated_pin_grid import (
    _SECTION_ID,
    paginated_pin_grid,
)
from pindb.templates.get.artist import artist_page

router = APIRouter()

_PER_PAGE: int = 100


@router.get(path="/artist/{id}", response_model=None)
def get_artist(
    request: Request,
    id: int,
    page: int = Query(default=1, ge=1),
) -> HTMLResponse | RedirectResponse:
    with session_maker.begin() as session:
        artist_obj: Artist | None = session.get(entity=Artist, ident=id)

        if not artist_obj:
            return RedirectResponse(url="/")

        offset: int = (page - 1) * _PER_PAGE

        total_count: int = (
            session.scalar(
                select(func.count(Pin.id))
                .join(pins_artists, Pin.id == pins_artists.c.pin_id)
                .where(pins_artists.c.artists_id == artist_obj.id)
            )
            or 0
        )

        pins: Sequence[Pin] = session.scalars(
            select(Pin)
            .join(pins_artists, Pin.id == pins_artists.c.pin_id)
            .where(pins_artists.c.artists_id == artist_obj.id)
            .order_by(Pin.name.asc())
            .limit(_PER_PAGE)
            .offset(offset)
        ).all()

        if request.headers.get("HX-Target") == _SECTION_ID:
            return HTMLResponse(
                content=str(
                    paginated_pin_grid(
                        request=request,
                        pins=pins,
                        total_count=total_count,
                        page=page,
                        page_url=str(request.url_for("get_artist", id=id)),
                        per_page=_PER_PAGE,
                    )
                )
            )

        return HTMLResponse(
            content=str(
                artist_page(
                    request=request,
                    artist=artist_obj,
                    pins=pins,
                    total_count=total_count,
                    page=page,
                    per_page=_PER_PAGE,
                )
            )
        )
