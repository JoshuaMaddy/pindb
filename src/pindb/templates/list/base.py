from fastapi import Request
from htpy import Element, div, hr, span

from pindb.models.list_view import EntityListView
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div
from pindb.templates.components.page_heading import page_heading
from pindb.templates.components.pagination_controls import pagination_controls
from pindb.templates.components.view_toggle import view_toggle

SECTION_ID: str = "entity-list-section"
DEFAULT_PER_PAGE: int = 100


def entity_list_section(
    items: list[Element],
    page: int,
    total_count: int,
    base_url: str,
    view: EntityListView,
    per_page: int = DEFAULT_PER_PAGE,
) -> Element:
    if view == EntityListView.grid:
        content: Element = div(
            class_="grid grid-cols-[repeat(auto-fill,_minmax(180px,_1fr))] gap-3"
        )[*items]
    else:
        content = div(class_="flex flex-col gap-2")[*items]

    return div(id=SECTION_ID)[
        div(class_="flex items-center justify-between mb-4")[
            view_toggle(
                base_url=base_url,
                current_view=view,
                section_id=SECTION_ID,
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
            extra_params={"view": view.value},
        ),
    ]


def base_list(
    title: str,
    icon: str,
    section: Element,
    bread_crumb: Element | None = None,
    request: Request | None = None,
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
                section,
            ],
            flex=True,
            col=True,
        ),
    )
