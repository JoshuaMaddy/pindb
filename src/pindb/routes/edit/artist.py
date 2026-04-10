from typing import Annotated

from fastapi import Form, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from pydantic import BeforeValidator

from pindb.database import Artist, session_maker
from pindb.database.link import Link
from pindb.model_utils import empty_str_list_to_none, empty_str_to_none
from pindb.templates.create_and_edit.artist import artist_form

router = APIRouter()


@router.get(path="/artist/{id}", response_model=None)
def get_edit_artist(
    request: Request,
    id: int,
) -> HTMLResponse | None:
    with session_maker.begin() as session:
        artist: Artist | None = session.get(entity=Artist, ident=id)

        if artist is None:
            return None

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
) -> HTMLResponse | None:
    with session_maker.begin() as session:
        artist: Artist | None = session.get(entity=Artist, ident=id)

        if not artist:
            return None

        artist.name = name
        artist.description = description

        for old_link in artist.links:
            session.delete(old_link)

        new_links: set[Link] = set()
        for new_link in links or []:
            new_links.add(Link(new_link))
        artist.links: set[Link] = new_links

        session.flush()
        artist_id: int = artist.id

    return HTMLResponse(
        headers={"HX-Redirect": str(request.url_for("get_artist", id=artist_id))}
    )
