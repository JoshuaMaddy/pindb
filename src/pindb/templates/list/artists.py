from typing import Sequence

from fastapi import Request
from htpy import Element, div, p, span

from pindb.database.artist import Artist
from pindb.models.list_view import EntityListView
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.card import card
from pindb.templates.components.entity_grid_card import entity_grid_card
from pindb.templates.components.thumbnail_grid import thumbnail_grid
from pindb.templates.list.base import DEFAULT_PER_PAGE, base_list, entity_list_section


def _grid_items(
    request: Request,
    artists: Sequence[Artist],
) -> list[Element]:
    return [
        entity_grid_card(
            request=request,
            href=str(request.url_for("get_artist", id=artist.id)),
            pins=artist.pins,
            name=("(P) " + artist.name) if artist.is_pending else artist.name,
        )
        for artist in artists
    ]


def _detailed_items(
    request: Request,
    artists: Sequence[Artist],
) -> list[Element]:
    return [
        card(
            href=request.url_for("get_artist", id=artist.id),
            content=div(class_="flex gap-2 w-full")[
                thumbnail_grid(request=request, pins=artist.pins),
                div[
                    p(class_="text-lg")[
                        ("(P) " + artist.name) if artist.is_pending else artist.name,
                        span(class_="text-pin-base-300 ml-1")[f"({len(artist.pins)})"],
                    ],
                    p(class_="text-pin-base-300")[artist.description],
                ],
            ],
        )
        for artist in artists
    ]


def artists_list_section(
    request: Request,
    artists: Sequence[Artist],
    view: EntityListView,
    page: int,
    total_count: int,
    base_url: str,
    per_page: int = DEFAULT_PER_PAGE,
) -> Element:
    items: list[Element] = (
        _grid_items(request=request, artists=artists)
        if view == EntityListView.grid
        else _detailed_items(request=request, artists=artists)
    )
    return entity_list_section(
        items=items,
        page=page,
        total_count=total_count,
        base_url=base_url,
        view=view,
        per_page=per_page,
    )


def artists_list(
    request: Request,
    artists: Sequence[Artist],
    view: EntityListView,
    page: int,
    total_count: int,
    base_url: str,
    per_page: int = DEFAULT_PER_PAGE,
) -> Element:
    return base_list(
        title="Artists",
        icon="palette",
        request=request,
        section=artists_list_section(
            request=request,
            artists=artists,
            view=view,
            page=page,
            total_count=total_count,
            base_url=base_url,
            per_page=per_page,
        ),
        bread_crumb=bread_crumb(
            entries=[
                (request.url_for("get_list_index"), "List"),
                "Artists",
            ]
        ),
    )
