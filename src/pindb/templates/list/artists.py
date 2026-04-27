"""
htpy page and fragment builders: `templates/list/artists.py`.
"""

from typing import Sequence

from fastapi import Request
from htpy import Element, div, p, span

from pindb.database.artist import Artist
from pindb.models.list_view import EntityListView
from pindb.models.sort_order import SortOrder
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.card import card
from pindb.templates.components.entity_grid_card import entity_grid_card
from pindb.templates.components.thumbnail_grid import thumbnail_grid
from pindb.templates.list.base import (
    DEFAULT_PER_PAGE,
    base_list,
    entity_list_section,
    list_search_input,
)


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
                        span(class_="text-lightest-hover ml-1")[
                            f"({len(artist.pins)})"
                        ],
                    ],
                    p(class_="text-lightest-hover")[artist.description],
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
    q: str = "",
    sort: SortOrder = SortOrder.name,
    per_page: int = DEFAULT_PER_PAGE,
) -> Element:
    items: list[Element] = (
        _grid_items(request=request, artists=artists)
        if view == EntityListView.grid
        else _detailed_items(request=request, artists=artists)
    )
    extra: dict[str, str] = {}
    if q:
        extra["q"] = q
    return entity_list_section(
        items=items,
        page=page,
        total_count=total_count,
        base_url=base_url,
        view=view,
        sort=sort,
        per_page=per_page,
        extra_params=extra or None,
    )


def artists_list(
    request: Request,
    artists: Sequence[Artist],
    view: EntityListView,
    page: int,
    total_count: int,
    base_url: str,
    q: str = "",
    sort: SortOrder = SortOrder.name,
    per_page: int = DEFAULT_PER_PAGE,
) -> Element:
    return base_list(
        title="Artists",
        icon="palette",
        request=request,
        search_controls=list_search_input(
            base_url=base_url,
            q=q,
            placeholder="Search artists…",
        ),
        section=artists_list_section(
            request=request,
            artists=artists,
            view=view,
            page=page,
            total_count=total_count,
            base_url=base_url,
            q=q,
            sort=sort,
            per_page=per_page,
        ),
        bread_crumb=bread_crumb(
            entries=[
                (request.url_for("get_list_index"), "List"),
                "Artists",
            ]
        ),
    )
