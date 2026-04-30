"""
FastAPI routes: `routes/edit/artist.py`.
"""

from typing import Annotated

from fastapi import Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from htpy.starlette import HtpyResponse
from pydantic import BeforeValidator
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pindb.auth import EditorUser
from pindb.database import Artist, async_session_maker
from pindb.database.artist import replace_artist_aliases
from pindb.database.entity_type import EntityType
from pindb.database.pending_edit_utils import (
    apply_snapshot_in_memory,
    get_edit_chain,
    get_effective_snapshot,
)
from pindb.htmx_toast import hx_redirect_with_toast_headers
from pindb.log import user_logger
from pindb.model_utils import empty_str_list_to_none, empty_str_to_none
from pindb.routes._guards import assert_editor_can_edit, needs_pending_edit
from pindb.routes._urls import slugify_for_url
from pindb.routes.edit._pending_helpers import (
    apply_simple_aliased_direct_edit,
    submit_simple_aliased_pending_edit,
)
from pindb.search.update import sync_entity
from pindb.templates.create_and_edit.artist import artist_form

router = APIRouter()

LOGGER = user_logger("pindb.routes.edit.artist")


@router.get(path="/artist/{id}", response_model=None)
async def get_edit_artist(
    request: Request,
    id: int,
    current_user: EditorUser,
) -> HtpyResponse:
    async with async_session_maker() as session:
        artist: Artist | None = await session.scalar(
            select(Artist)
            .where(Artist.id == id)
            .options(selectinload(Artist.links), selectinload(Artist.aliases))
        )

        if artist is None:
            raise HTTPException(status_code=404, detail="Artist not found")

        assert_editor_can_edit(artist, current_user)

        if needs_pending_edit(artist, current_user):
            chain = await get_edit_chain(session, "artists", id)
            if chain:
                effective = get_effective_snapshot(artist, chain)
                with session.no_autoflush:
                    await apply_snapshot_in_memory(artist, effective, session)

        return HtpyResponse(
            artist_form(
                post_url=request.url_for("post_edit_artist", id=id),
                artist=artist,
                request=request,
            )
        )


@router.post(path="/artist/{id}", response_model=None)
async def post_edit_artist(
    request: Request,
    id: int,
    current_user: EditorUser,
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
    async with async_session_maker.begin() as session:
        artist: Artist | None = await session.scalar(
            select(Artist)
            .where(Artist.id == id)
            .options(selectinload(Artist.links), selectinload(Artist.aliases))
        )

        if not artist:
            raise HTTPException(status_code=404, detail="Artist not found")

        assert_editor_can_edit(artist, current_user)

        if needs_pending_edit(artist, current_user):
            LOGGER.info("Submitting pending edit for artist id=%d name=%r", id, name)
            return await submit_simple_aliased_pending_edit(
                session=session,
                entity=artist,
                entity_table="artists",
                entity_id=id,
                name=name,
                description=description,
                links=links,
                aliases=aliases,
                current_user=current_user,
                request=request,
                redirect_route="get_artist",
            )

        LOGGER.info("Editing artist id=%d name=%r", id, name)
        await apply_simple_aliased_direct_edit(
            entity=artist,
            name=name,
            description=description,
            links=links,
            aliases=aliases,
            replace_aliases_fn=replace_artist_aliases,
            session=session,
        )

        await session.flush()
        artist_id: int = artist.id

    await sync_entity(EntityType.artist, artist_id)

    return HTMLResponse(
        headers=hx_redirect_with_toast_headers(
            redirect_url=str(
                request.url_for(
                    "get_artist",
                    slug=slugify_for_url(name=name, fallback="artist"),
                    id=artist_id,
                )
            ),
            message="Artist updated.",
        )
    )
