from typing import Annotated

from fastapi import Form, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from pydantic import BeforeValidator

from pindb.database import Artist, ArtistAlias, session_maker
from pindb.database.link import Link
from pindb.model_utils import empty_str_list_to_none, empty_str_to_none
from pindb.search.update import update_artist
from pindb.templates.create_and_edit.artist import artist_form

router = APIRouter()


@router.get(path="/artist")
def get_create_artist(request: Request) -> HTMLResponse:
    return HTMLResponse(
        content=artist_form(
            post_url=request.url_for("post_create_artist"),
            request=request,
        )
    )


@router.post(path="/artist")
def post_create_artist(
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
    with session_maker.begin() as session:
        new_links: set[Link] = (
            {Link(path=link) for link in links} if links else set[Link]()
        )

        artist = Artist(
            name=name,
            description=description,
            links=new_links,
        )

        session.add(instance=artist)
        session.flush()

        artist.aliases = [ArtistAlias(alias=a) for a in aliases if a.strip()]
        session.flush()
        artist_id: int = artist.id

    update_artist(artist=artist)

    return HTMLResponse(
        headers={
            "HX-Redirect": str(request.url_for("get_artist", id=artist_id)),
        }
    )
