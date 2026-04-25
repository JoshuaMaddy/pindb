"""
htpy page and fragment builders: `templates/list/shops.py`.
"""

from typing import Sequence

from fastapi import Request
from htpy import Element, div, p, span

from pindb.database.shop import Shop
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
    shops: Sequence[Shop],
) -> list[Element]:
    return [
        entity_grid_card(
            request=request,
            href=str(request.url_for("get_shop", id=shop.id)),
            pins=shop.pins,
            name=("(P) " + shop.name) if shop.is_pending else shop.name,
        )
        for shop in shops
    ]


def _detailed_items(
    request: Request,
    shops: Sequence[Shop],
) -> list[Element]:
    return [
        card(
            href=request.url_for("get_shop", id=shop.id),
            content=[
                thumbnail_grid(request=request, pins=shop.pins),
                div[
                    p(class_="text-lg")[
                        ("(P) " + shop.name) if shop.is_pending else shop.name,
                        span(class_="text-pin-base-300 ml-1")[f"({len(shop.pins)})"],
                    ],
                    p(class_="text-pin-base-300")[shop.description],
                ],
            ],
        )
        for shop in shops
    ]


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
    items: list[Element] = (
        _grid_items(request=request, shops=shops)
        if view == EntityListView.grid
        else _detailed_items(request=request, shops=shops)
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
    return base_list(
        title="Shops",
        icon="store",
        request=request,
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
        bread_crumb=bread_crumb(
            entries=[
                (request.url_for("get_list_index"), "List"),
                "Shops",
            ]
        ),
    )
