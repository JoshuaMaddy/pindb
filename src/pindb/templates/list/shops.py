"""
htpy page and fragment builders: `templates/list/shops.py`.
"""

from typing import Sequence

from fastapi import Request
from htpy import Element

from pindb.database.shop import Shop
from pindb.models.list_view import EntityListView
from pindb.models.sort_order import SortOrder
from pindb.routes._urls import shop_url
from pindb.templates.list.base import (
    DEFAULT_PER_PAGE,
    entity_list_items,
    entity_list_section,
    list_page,
    list_search_input,
)


def shops_list_section(
    request: Request,
    shops: Sequence[Shop],
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
        entities=shops,
        view=view,
        url_of=lambda shop: shop_url(request=request, shop=shop),
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


def shops_list(
    request: Request,
    shops: Sequence[Shop],
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
        title="Shops",
        icon="store",
        search_controls=list_search_input(
            base_url=base_url,
            q=q,
            placeholder="Search shops…",
        ),
        section=shops_list_section(
            request=request,
            shops=shops,
            view=view,
            page=page,
            total_count=total_count,
            base_url=base_url,
            q=q,
            sort=sort,
            per_page=per_page,
        ),
    )
