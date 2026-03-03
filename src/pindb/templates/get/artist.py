from fastapi import Request
from htpy import Element, a, br, div, fragment, h1, h2, i, p

from pindb.database import Artist
from pindb.templates.base import html_base
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.centered import centered_div
from pindb.templates.components.pin_grid import pin_grid


def artist_page(
    request: Request,
    artist: Artist,
) -> Element:
    return html_base(
        title=artist.name,
        body_content=centered_div(
            content=fragment[
                bread_crumb(
                    entries=[
                        (request.url_for("get_list_index"), "List"),
                        (request.url_for("get_list_artists"), "Artists"),
                        artist.name,
                    ]
                ),
                div(class_="flex w-full gap-2 items-baseline")[
                    i(data_lucide="palette"),
                    h1[artist.name],
                ],
                fragment[artist.description and div[p[artist.description]]],
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
                fragment[
                    bool(len(artist.pins)) and h2[f"All Pins ({len(artist.pins)})"],
                    pin_grid(
                        request=request,
                        pins=artist.pins,
                    ),
                ],
            ],
            flex=True,
            col=True,
        ),
    )
