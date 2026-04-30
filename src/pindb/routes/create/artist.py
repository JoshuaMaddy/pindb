"""
FastAPI routes: `routes/create/artist.py`.
"""

from typing import Annotated

from fastapi import Form, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from htpy.starlette import HtpyResponse
from pydantic import BeforeValidator
from sqlalchemy.exc import IntegrityError

from pindb.database import Artist, ArtistAlias, async_session_maker
from pindb.database.link import Link
from pindb.htmx_toast import (
    hx_redirect_with_toast_headers,
    is_unique_violation,
    unique_constraint_response,
)
from pindb.log import user_logger
from pindb.model_utils import empty_str_list_to_none, empty_str_to_none
from pindb.routes._urls import slugify_for_url
from pindb.search.update import update_artist
from pindb.templates.create_and_edit.artist import artist_form

router = APIRouter()

LOGGER = user_logger("pindb.routes.create.artist")


@router.get(path="/artist")
async def get_create_artist(request: Request) -> HtpyResponse:
    return HtpyResponse(
        artist_form(
            post_url=request.url_for("post_create_artist"),
            request=request,
        )
    )


@router.post(path="/artist")
async def post_create_artist(
    request: Request,
    name: str = Form(),
    description: Annotated[
        str | None,
        Form(),
        BeforeValidator(func=empty_str_to_none),
    ] = None,
    links: Annotated[
        list[str] | None,
        Form(),
        BeforeValidator(func=empty_str_list_to_none),
    ] = None,
    aliases: list[str] = Form(default_factory=list),
) -> HTMLResponse:
    LOGGER.info("Creating artist name=%r aliases=%s", name, aliases)
    try:
        async with async_session_maker.begin() as session:
            new_links: set[Link] = (
                {Link(path=link) for link in links} if links else set[Link]()
            )

            artist = Artist(
                name=name,
                description=description,
                links=new_links,
            )

            session.add(instance=artist)
            await session.flush()

            artist.aliases = [ArtistAlias(alias=a) for a in aliases if a.strip()]
            await session.flush()
            artist_id: int = artist.id
    except IntegrityError as exc:
        if not is_unique_violation(exc):
            raise
        return unique_constraint_response(request=request)

    await update_artist(artist=artist)

    LOGGER.info("Created artist id=%d name=%r", artist_id, name)

    return HTMLResponse(
        headers=hx_redirect_with_toast_headers(
            redirect_url=str(
                request.url_for(
                    "get_artist",
                    slug=slugify_for_url(name=name, fallback="artist"),
                    id=artist_id,
                )
            ),
            message="Artist created.",
        )
    )
