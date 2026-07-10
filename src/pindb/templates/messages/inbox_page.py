"""Full messages page: Inbox / Archived tabs, paginated list, mark-all-as-read.

``messages_list_section`` is the HTMX swap target (``#messages-list``); tab links
and pagination re-fetch ``GET /messages`` and replace just that section.
"""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import Request
from htpy import Element, a, div, hr

from pindb.templates.base import html_base
from pindb.templates.components.display.empty_state import empty_state
from pindb.templates.components.layout.centered import centered_div
from pindb.templates.components.layout.page_heading import page_heading
from pindb.templates.components.listing.pagination_controls import pagination_controls
from pindb.templates.messages.components import (
    MessageRow,
    Tab,
    mark_all_read_button,
    message_row,
)

PAGE_SIZE = 20
LIST_SECTION_ID = "messages-list"

_TAB_ACTIVE = "px-3 py-1 rounded border border-accent text-accent text-sm no-underline"
_TAB_INACTIVE = (
    "px-3 py-1 rounded border border-lightest text-lightest-hover text-sm "
    "hover:border-accent no-underline"
)


def _tab_link(request: Request, label: str, tab: Tab, current: Tab) -> Element:
    href = f"{request.url_for('get_messages')}?{urlencode({'tab': tab, 'page': '1'})}"
    return a(
        href=href,
        hx_get=href,
        hx_target=f"#{LIST_SECTION_ID}",
        hx_swap="outerHTML",
        hx_push_url="true",
        class_=_TAB_ACTIVE if tab == current else _TAB_INACTIVE,
    )[label]


def messages_list_section(
    request: Request,
    rows: list[MessageRow],
    *,
    total: int,
    page: int,
    tab: Tab,
) -> Element:
    """The paginated list of messages — the ``#messages-list`` swap target."""
    empty_message = "No messages yet." if tab == "inbox" else "No archived messages."
    pagination = pagination_controls(
        base_url=str(request.url_for("get_messages")),
        page=page,
        total_count=total,
        section_id=LIST_SECTION_ID,
        per_page=PAGE_SIZE,
        extra_params={"tab": tab},
    )
    return div(id=LIST_SECTION_ID, class_="flex w-full flex-col gap-2")[
        div(class_="flex flex-col gap-2")[
            [
                message_row(request, message, is_unread=is_unread, tab=tab)
                for message, is_unread in rows
            ]
        ]
        if rows
        else empty_state(empty_message),
        pagination,
    ]


def messages_page(
    request: Request,
    rows: list[MessageRow],
    *,
    total: int,
    page: int,
    tab: Tab,
    unread_exists: bool,
) -> Element:
    """The full messages page."""
    tabs = div(class_="flex gap-2", role="group", aria_label="Message folder")[
        _tab_link(request, "Inbox", "inbox", tab),
        _tab_link(request, "Archived", "archived", tab),
    ]
    controls = div(class_="flex items-center justify-between gap-2 flex-wrap")[
        tabs,
        tab == "inbox"
        and unread_exists
        and div(class_="w-auto shrink-0")[
            mark_all_read_button(request, target=LIST_SECTION_ID)
        ],
    ]
    return html_base(
        title="Messages",
        request=request,
        body_content=centered_div(
            content=[
                div(class_="flex w-full min-w-0 flex-col gap-2")[
                    page_heading(
                        icon="mail",
                        text="Messages",
                        level=1,
                        heading_id="messages-heading",
                    ),
                    controls,
                ],
                hr,
                messages_list_section(request, rows, total=total, page=page, tab=tab),
            ],
            flex=True,
            col=True,
        ),
    )
