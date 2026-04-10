from typing import Sequence

from fastapi import Request
from htpy import Element, a, br, div, fragment, h2

from pindb.database import Artist
from pindb.database.pin import Pin
from pindb.templates.base import html_base
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.centered import centered_div
from pindb.templates.components.description_block import description_block
from pindb.templates.components.page_heading import page_heading
from pindb.templates.components.paginated_pin_grid import paginated_pin_grid


def artist_page(
    request: Request,
    artist: Artist,
    pins: Sequence[Pin],
    total_count: int,
    page: int,
    per_page: int,
) -> Element:
    return html_base(
        title=artist.name,
        request=request,
        body_content=centered_div(
            content=fragment[
                bread_crumb(
                    entries=[
                        (request.url_for("get_list_index"), "List"),
                        (request.url_for("get_list_artists"), "Artists"),
                        artist.name,
                    ]
                ),
                page_heading(
                    icon="palette",
                    text=artist.name,
                    full_width=True,
                ),
                description_block(artist.description),
                fragment[
                    bool(len(artist.links))
                    and div[
                        h2["Links"],
                        *[
                            fragment[a(href=link.path)[link.path], br]
                            for link in artist.links
                        ],
                    ]
                ],
                paginated_pin_grid(
                    request=request,
                    pins=pins,
                    total_count=total_count,
                    page=page,
                    page_url=str(request.url_for("get_artist", id=artist.id)),
                    per_page=per_page,
                ),
            ],
            flex=True,
            col=True,
        ),
    )
