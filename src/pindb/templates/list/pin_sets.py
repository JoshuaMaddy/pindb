from typing import Sequence

from fastapi import Request
from htpy import Element, div, p, span

from pindb.database.pin_set import PinSet
from pindb.models.list_view import EntityListView
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
    pin_sets: Sequence[PinSet],
) -> list[Element]:
    return [
        entity_grid_card(
            request=request,
            href=str(request.url_for("get_pin_set", id=pin_set.id)),
            pins=pin_set.pins,
            name=("(P) " + pin_set.name) if pin_set.is_pending else pin_set.name,
        )
        for pin_set in pin_sets
    ]


def _detailed_items(
    request: Request,
    pin_sets: Sequence[PinSet],
) -> list[Element]:
    return [
        card(
            href=request.url_for("get_pin_set", id=pin_set.id),
            content=div(class_="flex gap-2 w-full")[
                thumbnail_grid(request=request, pins=pin_set),
                div[
                    p(class_="text-lg")[
                        ("(P) " + pin_set.name) if pin_set.is_pending else pin_set.name,
                        span(class_="text-pin-base-300 ml-1")[f"({len(pin_set.pins)})"],
                    ],
                    p(class_="text-pin-base-300")[pin_set.description],
                ],
            ],
        )
        for pin_set in pin_sets
    ]


def pin_sets_list_section(
    request: Request,
    pin_sets: Sequence[PinSet],
    view: EntityListView,
    page: int,
    total_count: int,
    base_url: str,
    q: str = "",
    per_page: int = DEFAULT_PER_PAGE,
) -> Element:
    items: list[Element] = (
        _grid_items(request=request, pin_sets=pin_sets)
        if view == EntityListView.grid
        else _detailed_items(request=request, pin_sets=pin_sets)
    )
    extra: dict[str, str] | None = {"q": q} if q else None
    return entity_list_section(
        items=items,
        page=page,
        total_count=total_count,
        base_url=base_url,
        view=view,
        per_page=per_page,
        extra_params=extra,
    )


def pin_sets_list(
    request: Request,
    pin_sets: Sequence[PinSet],
    view: EntityListView,
    page: int,
    total_count: int,
    base_url: str,
    q: str = "",
    per_page: int = DEFAULT_PER_PAGE,
) -> Element:
    return base_list(
        title="Pin Sets",
        icon="layout-grid",
        request=request,
        search_controls=list_search_input(
            base_url=base_url,
            q=q,
            placeholder="Search pin sets…",
        ),
        section=pin_sets_list_section(
            request=request,
            pin_sets=pin_sets,
            view=view,
            page=page,
            total_count=total_count,
            base_url=base_url,
            q=q,
            per_page=per_page,
        ),
        bread_crumb=bread_crumb(
            entries=[
                (request.url_for("get_list_index"), "List"),
                "Pin Sets",
            ]
        ),
    )
