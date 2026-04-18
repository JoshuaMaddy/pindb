from typing import Annotated

from fastapi import Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from pydantic import BeforeValidator
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from pindb.auth import EditorUser
from pindb.database import Artist, ArtistAlias, session_maker
from pindb.database.pending_edit_utils import (
    apply_snapshot_in_memory,
    get_edit_chain,
    get_effective_snapshot,
)
from pindb.log import user_logger
from pindb.model_utils import empty_str_list_to_none, empty_str_to_none
from pindb.routes._guards import assert_editor_can_edit, needs_pending_edit
from pindb.routes.edit._pending_helpers import replace_links, submit_pending_edit
from pindb.templates.create_and_edit.artist import artist_form

router = APIRouter()

LOGGER = user_logger("pindb.routes.edit.artist")


@router.get(path="/artist/{id}", response_model=None)
def get_edit_artist(
    request: Request,
    id: int,
    current_user: EditorUser,
) -> HTMLResponse:
    with session_maker() as session:
        artist: Artist | None = session.scalar(
            select(Artist)
            .where(Artist.id == id)
            .options(selectinload(Artist.links), selectinload(Artist.aliases))
        )

        if artist is None:
            raise HTTPException(status_code=404, detail="Artist not found")

        assert_editor_can_edit(artist, current_user)

        if needs_pending_edit(artist, current_user):
            chain = get_edit_chain(session, "artists", id)
            if chain:
                effective = get_effective_snapshot(artist, chain)
                with session.no_autoflush:
                    apply_snapshot_in_memory(artist, effective, session)

        return HTMLResponse(
            content=artist_form(
                post_url=request.url_for("post_edit_artist", id=id),
                artist=artist,
                request=request,
            )
        )


@router.post(path="/artist/{id}", response_model=None)
def post_edit_artist(
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
    with session_maker.begin() as session:
        artist: Artist | None = session.scalar(
            select(Artist)
            .where(Artist.id == id)
            .options(selectinload(Artist.links), selectinload(Artist.aliases))
        )

        if not artist:
            raise HTTPException(status_code=404, detail="Artist not found")

        assert_editor_can_edit(artist, current_user)

        if needs_pending_edit(artist, current_user):
            LOGGER.info("Submitting pending edit for artist id=%d name=%r", id, name)
            return submit_pending_edit(
                session=session,
                entity=artist,
                entity_table="artists",
                entity_id=id,
                field_updates={
                    "name": name,
                    "description": description,
                    "links": sorted(links or []),
                    "aliases": sorted(alias for alias in aliases if alias.strip()),
                },
                current_user=current_user,
                request=request,
                redirect_route="get_artist",
            )

        LOGGER.info("Editing artist id=%d name=%r", id, name)
        artist.name = name
        artist.description = description

        replace_links(entity=artist, urls=links, session=session)

        artist.aliases = [
            ArtistAlias(alias=alias) for alias in aliases if alias.strip()
        ]

        session.flush()
        artist_id: int = artist.id

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_artist", id=artist_id))}
    )
