from typing import Sequence

from fastapi import Request
from htpy import Element, div, p, span

from pindb.database.tag import Tag
from pindb.models.list_view import EntityListView
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.card import card
from pindb.templates.components.entity_grid_card import entity_grid_card
from pindb.templates.components.thumbnail_grid import thumbnail_grid
from pindb.templates.list.base import DEFAULT_PER_PAGE, base_list, entity_list_section


def _grid_items(
    request: Request,
    tags: Sequence[Tag],
) -> list[Element]:
    return [
        entity_grid_card(
            request=request,
            href=str(request.url_for("get_tag", id=tag.id)),
            pins=tag.pins,
            name=tag.name,
        )
        for tag in tags
    ]


def _detailed_items(
    request: Request,
    tags: Sequence[Tag],
) -> list[Element]:
    return [
        card(
            href=request.url_for("get_tag", id=tag.id),
            content=div(class_="flex gap-2 w-full")[
                thumbnail_grid(request=request, pins=tag.pins),
                p(class_="text-lg")[
                    tag.name,
                    span(class_="text-pin-base-300 ml-1")[f"({len(tag.pins)})"],
                ],
            ],
        )
        for tag in tags
    ]


def tags_list_section(
    request: Request,
    tags: Sequence[Tag],
    view: EntityListView,
    page: int,
    total_count: int,
    base_url: str,
    per_page: int = DEFAULT_PER_PAGE,
) -> Element:
    items: list[Element] = (
        _grid_items(request=request, tags=tags)
        if view == EntityListView.grid
        else _detailed_items(request=request, tags=tags)
    )
    return entity_list_section(
        items=items,
        page=page,
        total_count=total_count,
        base_url=base_url,
        view=view,
        per_page=per_page,
    )


def tags_list(
    request: Request,
    tags: Sequence[Tag],
    view: EntityListView,
    page: int,
    total_count: int,
    base_url: str,
    per_page: int = DEFAULT_PER_PAGE,
) -> Element:
    return base_list(
        title="Tags",
        icon="tag",
        request=request,
        section=tags_list_section(
            request=request,
            tags=tags,
            view=view,
            page=page,
            total_count=total_count,
            base_url=base_url,
            per_page=per_page,
        ),
        bread_crumb=bread_crumb(
            entries=[
                (request.url_for("get_list_index"), "List"),
                "Tags",
            ]
        ),
    )
