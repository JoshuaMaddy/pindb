"""
htpy page and fragment builders: `templates/list/base.py`.
"""

from fastapi import Request
from htpy import Element, VoidElement, div, hr, input, span

from pindb.models.list_view import EntityListView
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div
from pindb.templates.components.page_heading import page_heading
from pindb.templates.components.pagination_controls import pagination_controls
from pindb.templates.components.view_toggle import view_toggle

SECTION_ID: str = "entity-list-section"
DEFAULT_PER_PAGE: int = 100
TABLE_LIST_SCROLL: str = "w-full min-w-0 overflow-x-auto"


def list_search_input(
    base_url: str,
    q: str = "",
    placeholder: str = "Search…",
) -> VoidElement:
    """HTMX search input that replaces #entity-list-section on typing (500ms debounce).

    Uses hx-include to pull the current view and category hidden inputs from
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
        hx_include=f"#{SECTION_ID} [name='view'], #{SECTION_ID} [name='category']",
        class_=(
            "bg-pin-base-450 border border-pin-base-400 rounded px-3 py-1.5 text-pin-base-text w-full"
        ),
    )


def entity_list_section(
    items: list[Element],
    page: int,
    total_count: int,
    base_url: str,
    view: EntityListView,
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

    pagination_extra: dict[str, str] = {"view": view.value}
    if extra_params:
        pagination_extra.update(extra_params)

    return div(id=SECTION_ID)[
        # Hidden view input — picked up by search input via hx-include
        input(type="hidden", name="view", value=view.value),
        # Any additional hidden inputs (e.g. category for tags)
        *(extra_hidden or []),
        div(class_="flex items-center justify-between mb-4")[
            view_toggle(
                base_url=base_url,
                current_view=view,
                section_id=SECTION_ID,
                extra_params=extra_params,
            ),
            span(class_="text-sm text-pin-base-300")[f"{total_count} items"],
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
