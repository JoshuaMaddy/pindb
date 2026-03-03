from typing import Sequence

from fastapi import Request
from htpy import Element, a

from pindb.database.artist import Artist
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.list.base import base_list


def artists_list(request: Request, artists: Sequence[Artist]) -> Element:
    return base_list(
        title="Artists",
        items=[
            a(href=str(request.url_for("get_artist", id=artist.id)))[artist.name]
            for artist in artists
        ],
        bread_crumb=bread_crumb(
            entries=[
                (request.url_for("get_list_index"), "List"),
                "Artists",
            ]
        ),
    )
