"""
htpy page and fragment builders: `templates/list/tags.py`.
"""

from typing import Sequence

from fastapi import Request
from htpy import Element, div, input, option, p, select, span

from pindb.database.tag import Tag, TagCategory
from pindb.models.list_view import EntityListView
from pindb.models.sort_order import SortOrder
from pindb.templates.components.layout.card import card
from pindb.templates.components.nav.bread_crumb import bread_crumb
from pindb.templates.components.pins.entity_grid_card import entity_grid_card
from pindb.templates.components.pins.thumbnail_grid import thumbnail_grid
from pindb.templates.get.tag import category_badge
from pindb.templates.list.base import (
    DEFAULT_PER_PAGE,
    base_list,
    entity_list_section,
    list_search_input,
)


def _grid_items(
    request: Request,
    tags: Sequence[Tag],
) -> list[Element]:
    return [
        entity_grid_card(
            request=request,
            href=str(request.url_for("get_tag", id=tag.id)),
            pins=tag.pins,
            name=("(P) " + tag.display_name) if tag.is_pending else tag.display_name,
            badge=category_badge(
                tag.category,
                additional_classes="max-md:absolute max-md:-top-2 max-md:-right-2",
            ),
            allow_overflow=True,
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
            content=div(class_="flex gap-2 w-full items-start")[
                thumbnail_grid(request=request, pins=tag.pins),
                div(class_="flex gap-2")[
                    p(class_="text-lg")[
                        ("(P) " + tag.display_name)
                        if tag.is_pending
                        else tag.display_name,
                        span(class_="text-lightest-hover ml-1")[f"({len(tag.pins)})"],
                    ],
                    category_badge(tag.category),
                ],
            ],
        )
        for tag in tags
    ]


def _category_select(base_url: str, category: TagCategory | None) -> Element:
    """Category dropdown — fires section swap on change, preserves current view and q."""
    from pindb.templates.list.base import SECTION_ID

    return select(
        name="category",
        hx_get=base_url,
        hx_trigger="change",
        hx_target=f"#{SECTION_ID}",
        hx_swap="outerHTML",
        hx_replace_url="true",
        hx_include=f"#{SECTION_ID} [name='view'], #{SECTION_ID} [name='sort'], [name='q']",
        class_=(
            "bg-lighter border border-lightest rounded px-2 py-1.5 "
            "text-base-text text-sm"
        ),
    )[
        option(value="", selected=(category is None))["All categories"],
        *[
            option(value=cat.value, selected=(category == cat))[cat.value.capitalize()]
            for cat in TagCategory
        ],
    ]


def _tag_search_controls(
    base_url: str,
    q: str,
    category: TagCategory | None,
) -> Element:
    return div(class_="flex gap-2 items-center")[
        list_search_input(base_url=base_url, q=q, placeholder="Search tags…"),
        _category_select(base_url=base_url, category=category),
    ]


def tags_list_section(
    request: Request,
    tags: Sequence[Tag],
    view: EntityListView,
    page: int,
    total_count: int,
    base_url: str,
    q: str = "",
    category: TagCategory | None = None,
    sort: SortOrder = SortOrder.name,
    per_page: int = DEFAULT_PER_PAGE,
) -> Element:
    items: list[Element] = (
        _grid_items(request=request, tags=tags)
        if view == EntityListView.grid
        else _detailed_items(request=request, tags=tags)
    )
    extra: dict[str, str] = {}
    if q:
        extra["q"] = q
    if category:
        extra["category"] = category.value

    return entity_list_section(
        items=items,
        page=page,
        total_count=total_count,
        base_url=base_url,
        view=view,
        sort=sort,
        per_page=per_page,
        extra_params=extra or None,
        extra_hidden=[
            input(
                type="hidden",
                name="category",
                value=category.value if category else "",
            )
        ],
    )


def tags_list(
    request: Request,
    tags: Sequence[Tag],
    view: EntityListView,
    page: int,
    total_count: int,
    base_url: str,
    q: str = "",
    category: TagCategory | None = None,
    sort: SortOrder = SortOrder.name,
    per_page: int = DEFAULT_PER_PAGE,
) -> Element:
    return base_list(
        title="Tags",
        icon="tag",
        request=request,
        search_controls=_tag_search_controls(
            base_url=base_url,
            q=q,
            category=category,
        ),
        section=tags_list_section(
            request=request,
            tags=tags,
            view=view,
            page=page,
            total_count=total_count,
            base_url=base_url,
            q=q,
            category=category,
            sort=sort,
            per_page=per_page,
        ),
        bread_crumb=bread_crumb(
            entries=[
                (request.url_for("get_list_index"), "List"),
                "Tags",
            ]
        ),
    )
