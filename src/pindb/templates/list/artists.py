"""
htpy page and fragment builders: `templates/list/artists.py`.
"""

from typing import Sequence

from fastapi import Request
from htpy import Element

from pindb.database.artist import Artist
from pindb.database.pin_previews import PinPreviews
from pindb.models.list_view import EntityListView
from pindb.models.sort_order import SortOrder
from pindb.routes._urls import artist_url
from pindb.templates.list.base import (
    DEFAULT_PER_PAGE,
    entity_list_items,
    entity_list_section,
    list_page,
    list_search_input,
)


def artists_list_section(
    request: Request,
    artists: Sequence[Artist],
    previews: PinPreviews,
    view: EntityListView,
    page: int,
    total_count: int,
    base_url: str,
    q: str = "",
    sort: SortOrder = SortOrder.name,
    per_page: int = DEFAULT_PER_PAGE,
) -> Element:
    items = entity_list_items(
        request=request,
        entities=artists,
        previews=previews,
        view=view,
        url_of=lambda artist: artist_url(request=request, artist=artist),
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
    previews: PinPreviews,
    view: EntityListView,
    page: int,
    total_count: int,
    base_url: str,
    q: str = "",
    sort: SortOrder = SortOrder.name,
    per_page: int = DEFAULT_PER_PAGE,
) -> Element:
    return list_page(
        request=request,
        title="Artists",
        icon="palette",
        search_controls=list_search_input(
            base_url=base_url,
            q=q,
            placeholder="Search artists…",
        ),
        section=artists_list_section(
            request=request,
            artists=artists,
            previews=previews,
            view=view,
            page=page,
            total_count=total_count,
            base_url=base_url,
            q=q,
            sort=sort,
            per_page=per_page,
        ),
    )
