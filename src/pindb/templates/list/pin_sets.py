"""
htpy page and fragment builders: `templates/list/pin_sets.py`.
"""

from typing import Sequence

from fastapi import Request
from htpy import Element

from pindb.database.pin_previews import PinPreviews
from pindb.database.pin_set import PinSet
from pindb.models.list_view import EntityListView
from pindb.models.sort_order import SortOrder
from pindb.routes._urls import pin_set_url
from pindb.templates.list.base import (
    DEFAULT_PER_PAGE,
    entity_list_items,
    entity_list_section,
    list_page,
    list_search_input,
)


def pin_sets_list_section(
    request: Request,
    pin_sets: Sequence[PinSet],
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
        entities=pin_sets,
        previews=previews,
        view=view,
        url_of=lambda pin_set: pin_set_url(request=request, pin_set=pin_set),
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


def pin_sets_list(
    request: Request,
    pin_sets: Sequence[PinSet],
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
        title="Pin Sets",
        icon="layout-grid",
        search_controls=list_search_input(
            base_url=base_url,
            q=q,
            placeholder="Search pin sets…",
        ),
        section=pin_sets_list_section(
            request=request,
            pin_sets=pin_sets,
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
