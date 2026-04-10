from typing import Sequence

from fastapi import Request
from htpy import Element, div, p

from pindb.database.artist import Artist
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.card import card
from pindb.templates.components.thumbnail_grid import thumbnail_grid
from pindb.templates.list.base import base_list


def artists_list(
    request: Request,
    artists: Sequence[Artist],
) -> Element:
    return base_list(
        title="Artists",
        request=request,
        items=[
            card(
                href=request.url_for("get_artist", id=artist.id),
                content=div(class_="flex gap-2 w-full")[
                    thumbnail_grid(request, artist.pins),
                    div[
                        p(class_="text-lg")[artist.name],
                        p(class_="text-pin-base-300")[artist.description],
                    ],
                ],
            )
            for artist in artists
        ],
        bread_crumb=bread_crumb(
            entries=[
                (request.url_for("get_list_index"), "List"),
                "Artists",
            ]
        ),
    )
