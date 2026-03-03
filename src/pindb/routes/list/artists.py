from typing import Sequence

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from sqlalchemy import select

from pindb.database import Artist, session_maker
from pindb.templates.list.artists import artists_list

router = APIRouter()


@router.get(path="/artists")
def get_list_artists(request: Request) -> HTMLResponse:
    with session_maker.begin() as session:
        artists: Sequence[Artist] = session.scalars(
            statement=select(Artist).order_by(Artist.name.asc())
        ).all()

        return HTMLResponse(content=artists_list(request=request, artists=artists))
