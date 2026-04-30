"""
FastAPI routes: `routes/get/artist.py`.
"""

from typing import Sequence

from fastapi import Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.routing import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from pindb.auth import CurrentUser
from pindb.database import Artist, Pin, async_session_maker
from pindb.database.joins import pins_artists
from pindb.database.pending_edit_utils import maybe_apply_pending_view
from pindb.routes._urls import artist_url, canonical_slug_redirect, slugify_for_url
from pindb.templates.components.pins.paginated_pin_grid import (
    _SECTION_ID,
    paginated_pin_grid,
)
from pindb.templates.get.artist import artist_page

router = APIRouter()

_PER_PAGE: int = 100


@router.get(path="/artist/{slug}/{id}", response_model=None, name="get_artist")
@router.get(
    path="/artist/{id}",
    response_model=None,
    name="get_artist_by_id",
    include_in_schema=False,
)
async def get_artist(
    request: Request,
    id: int,
    current_user: CurrentUser,
    slug: str | None = None,
    page: int = Query(default=1, ge=1),
    version: str | None = Query(default=None),
) -> HTMLResponse | RedirectResponse:
    async with async_session_maker() as session:
        artist_obj: Artist | None = await session.scalar(
            select(Artist)
            .where(Artist.id == id)
            .options(selectinload(Artist.links), selectinload(Artist.aliases))
        )

        if not artist_obj:
            return RedirectResponse(url="/")

        canonical_slug: str = slugify_for_url(name=artist_obj.name, fallback="artist")
        if slug != canonical_slug:
            return canonical_slug_redirect(
                request=request,
                route_name="get_artist",
                canonical_slug=canonical_slug,
                id=id,
            )

        pending_chain_exists, viewing_pending = await maybe_apply_pending_view(
            session=session,
            entity=artist_obj,
            entity_table="artists",
            current_user=current_user,
            version=version,
        )

        offset: int = (page - 1) * _PER_PAGE

        total_count: int = (
            await session.scalar(
                select(func.count(Pin.id))
                .join(pins_artists, Pin.id == pins_artists.c.pin_id)
                .where(pins_artists.c.artists_id == artist_obj.id)
            )
            or 0
        )

        pins: Sequence[Pin] = (
            await session.scalars(
                select(Pin)
                .join(pins_artists, Pin.id == pins_artists.c.pin_id)
                .where(pins_artists.c.artists_id == artist_obj.id)
                .order_by(Pin.name.asc())
                .limit(_PER_PAGE)
                .offset(offset)
            )
        ).all()

        if request.headers.get("HX-Target") == _SECTION_ID:
            return HTMLResponse(
                content=str(
                    paginated_pin_grid(
                        request=request,
                        pins=pins,
                        total_count=total_count,
                        page=page,
                        page_url=str(artist_url(request=request, artist=artist_obj)),
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
                    has_pending_chain=pending_chain_exists,
                    viewing_pending=viewing_pending,
                )
            )
        )
