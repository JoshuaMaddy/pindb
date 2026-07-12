"""
htpy page and fragment builders: `templates/list/base.py`.
"""

from collections.abc import Callable, Sequence
from typing import TypeVar
from urllib.parse import urlencode

from fastapi import Request
from htpy import Element, VoidElement, a, div, hr, i, input, p, span
from starlette.datastructures import URL

from pindb.database.artist import Artist
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.models.list_view import EntityListView
from pindb.models.sort_order import SortOrder
from pindb.templates.base import html_base
from pindb.templates.components.layout.card import card
from pindb.templates.components.layout.centered import centered_div
from pindb.templates.components.layout.page_heading import page_heading
from pindb.templates.components.listing.pagination_controls import pagination_controls
from pindb.templates.components.listing.view_toggle import view_toggle
from pindb.templates.components.nav.bread_crumb import bread_crumb
from pindb.templates.components.pins.entity_grid_card import entity_grid_card
from pindb.templates.components.pins.thumbnail_grid import thumbnail_grid
from pindb.utils import review_label

SECTION_ID: str = "entity-list-section"
DEFAULT_PER_PAGE: int = 100
TABLE_LIST_SCROLL: str = "w-full min-w-0 overflow-x-auto"

_SORT_LABELS: dict[SortOrder, str] = {
    SortOrder.name: "Name",
    SortOrder.newest: "Newest",
    SortOrder.oldest: "Oldest",
}
# Direction chevron per sort: up = ascending, down = descending. Shown on every
# option so the sort direction is always legible, not just the active one.
_SORT_CHEVRON: dict[SortOrder, str] = {
    SortOrder.name: "chevron-up",  # A → Z
    SortOrder.newest: "chevron-down",  # newest first (created desc)
    SortOrder.oldest: "chevron-up",  # oldest first (created asc)
}


def _result_range_label(*, page: int, per_page: int, shown: int, total: int) -> str:
    """Human range like ``Showing 1–24 of 137`` for the current page slice."""
    if total <= 0 or shown <= 0:
        return "No items"
    start = (page - 1) * per_page + 1
    end = start + shown - 1
    return f"Showing {start}–{end} of {total}"


_ACTIVE_CLASS: str = (
    "px-3 py-1 rounded border border-accent text-accent text-sm no-underline"
)
_INACTIVE_CLASS: str = (
    "px-3 py-1 rounded border border-lightest text-lightest-hover text-sm "
    "hover:border-accent no-underline"
)


def _sort_control(
    base_url: str,
    current_sort: SortOrder,
    extra_params: dict[str, str] | None = None,
) -> Element:
    def _link(sort: SortOrder) -> Element:
        params: dict[str, str] = {"sort": sort.value, "page": "1"}
        if extra_params:
            params.update(extra_params)
        href = f"{base_url}?{urlencode(params)}"
        active = current_sort == sort
        return a(
            href=href,
            hx_get=href,
            hx_target=f"#{SECTION_ID}",
            hx_swap="outerHTML",
            hx_push_url="true",
            aria_current="true" if active else None,
            class_=(_ACTIVE_CLASS if active else _INACTIVE_CLASS)
            + " inline-flex items-center gap-1",
        )[
            _SORT_LABELS[sort],
            i(
                data_lucide=_SORT_CHEVRON[sort],
                class_="inline-block w-4 h-4",
                aria_hidden="true",
            ),
        ]

    return div(class_="flex items-center gap-1", role="group", aria_label="Sort")[
        span(class_="text-sm text-lightest-hover mr-0.5")["Sort:"],
        _link(SortOrder.name),
        _link(SortOrder.newest),
        _link(SortOrder.oldest),
    ]


def list_search_input(
    base_url: str,
    q: str = "",
    placeholder: str = "Search…",
) -> VoidElement:
    """HTMX search input that replaces #entity-list-section on typing (500ms debounce).

    Uses hx-include to pull the current view, category, and sort hidden inputs from
    inside the section, so those values survive across searches.
    """
    return input(
        type="search",
        name="q",
        value=q,
        placeholder=placeholder,
        hx_get=base_url,
        hx_trigger="input changed delay:500ms, search",
        hx_target=f"#{SECTION_ID}",
        hx_swap="outerHTML",
        hx_replace_url="true",
        hx_include=(
            f"#{SECTION_ID} [name='view'], "
            f"#{SECTION_ID} [name='category'], "
            f"#{SECTION_ID} [name='sort']"
        ),
        aria_label="Search",
        class_=(
            "bg-lighter border border-lightest rounded px-3 py-1.5 text-base-text w-full"
        ),
    )


def entity_list_section(
    items: list[Element],
    page: int,
    total_count: int,
    base_url: str,
    view: EntityListView,
    sort: SortOrder = SortOrder.name,
    per_page: int = DEFAULT_PER_PAGE,
    extra_params: dict[str, str] | None = None,
    extra_hidden: list[Element | VoidElement] | None = None,
) -> Element:
    if view == EntityListView.grid:
        content: Element = div(
            class_=(
                "grid grid-cols-[repeat(auto-fill,_minmax(100px,_1fr))] "
                "sm:grid-cols-[repeat(auto-fill,_minmax(180px,_1fr))] gap-3"
            )
        )[*items]
    else:
        # overflow-visible so card hover:scale does not clip or spawn scrollbars
        content = div(class_="flex w-full min-w-0 flex-col gap-2 overflow-visible")[
            *items,
        ]

    # extra_params from callers contains q, category — not view or sort
    view_toggle_extra: dict[str, str] = dict(extra_params or {})
    view_toggle_extra["sort"] = sort.value  # view_toggle adds "view" itself

    source_control_extra: dict[str, str] = dict(extra_params or {})
    source_control_extra["view"] = view.value  # sort_control adds "sort" itself

    pagination_extra: dict[str, str] = {"view": view.value, "sort": sort.value}
    pagination_extra.update(extra_params or {})

    return div(
        id=SECTION_ID,
        role="region",
        aria_label="Directory results",
    )[
        # Hidden inputs — picked up by search input via hx-include
        input(type="hidden", name="view", value=view.value),
        input(type="hidden", name="sort", value=sort.value),
        # Any additional hidden inputs (e.g. category for tags)
        *(extra_hidden or []),
        div(class_="relative")[
            div(class_="flex items-center justify-between overflow-x-auto")[
                div(class_="flex items-center gap-3")[
                    view_toggle(
                        base_url=base_url,
                        current_view=view,
                        section_id=SECTION_ID,
                        extra_params=view_toggle_extra,
                    ),
                    _sort_control(
                        base_url=base_url,
                        current_sort=sort,
                        extra_params=source_control_extra,
                    ),
                ],
            ],
            div(
                class_=(
                    "absolute right-0 top-0 bottom-0 w-10 z-10 pointer-events-none"
                    " bg-gradient-to-r from-transparent to-[var(--color-darker)]"
                )
            ),
        ],
        span(class_="text-sm text-lightest-hover")[
            _result_range_label(
                page=page,
                per_page=per_page,
                shown=len(items),
                total=total_count,
            )
        ],
        content,
        pagination_controls(
            base_url=base_url,
            page=page,
            total_count=total_count,
            section_id=SECTION_ID,
            per_page=per_page,
            extra_params=pagination_extra,
        ),
    ]


_BrowseEntity = TypeVar("_BrowseEntity", Shop, Artist, PinSet)


def entity_list_items(
    *,
    request: Request,
    entities: Sequence[_BrowseEntity],
    view: EntityListView,
    url_of: Callable[[_BrowseEntity], URL],
) -> list[Element]:
    """Grid or detailed cards for a simple browse entity (shop / artist / pin set).

    These three render identically apart from their canonical URL, so the only
    per-entity input is ``url_of``. ``name``/``description``/``pins``/
    ``is_pending`` are read directly. (Tags differ — category badge, extra
    filter — and keep their own builders.)
    """
    if view == EntityListView.grid:
        return [
            entity_grid_card(
                request=request,
                href=str(url_of(entity)),
                pins=entity.pins,
                name=review_label(
                    entity.name,
                    is_pending=entity.is_pending,
                    is_rejected=entity.is_rejected,
                ),
            )
            for entity in entities
        ]
    return [
        card(
            href=url_of(entity),
            content=div(class_="flex gap-2 w-full")[
                thumbnail_grid(request=request, pins=entity.pins),
                div[
                    p(class_="text-lg")[
                        review_label(
                            entity.name,
                            is_pending=entity.is_pending,
                            is_rejected=entity.is_rejected,
                        ),
                        span(class_="text-lightest-hover ml-1")[
                            f"({len(entity.pins)})"
                        ],
                    ],
                    p(class_="text-lightest-hover")[entity.description],
                ],
            ],
        )
        for entity in entities
    ]


def list_page(
    *,
    request: Request,
    title: str,
    icon: str,
    search_controls: Element | VoidElement,
    section: Element,
    breadcrumb_label: str | None = None,
) -> Element:
    """Full directory page wrapper shared by every entity list template.

    Builds the standard ``List > <title>`` breadcrumb and delegates layout to
    ``base_list``. ``breadcrumb_label`` defaults to ``title``.
    """
    return base_list(
        title=title,
        icon=icon,
        request=request,
        search_controls=search_controls,
        section=section,
        bread_crumb=bread_crumb(
            entries=[
                (request.url_for("get_list_index"), "List"),
                breadcrumb_label or title,
            ]
        ),
    )


def base_list(
    title: str,
    icon: str,
    section: Element,
    bread_crumb: Element | None = None,
    request: Request | None = None,
    search_controls: Element | VoidElement | None = None,
) -> Element:
    return html_base(
        title=title,
        request=request,
        body_content=centered_div(
            content=[
                bread_crumb,
                page_heading(
                    icon=icon,
                    text=title,
                    full_width=True,
                ),
                hr,
                search_controls,
                section,
            ],
            flex=True,
            col=True,
        ),
    )
