"""Shared message-row + action builders used by both the inbox page and the
navbar preview. Kept free of ``templates.base`` so the navbar (which renders the
preview) can import it without a circular import through ``html_base``.
"""

from __future__ import annotations

from typing import Literal

from fastapi import Request
from htpy import Element, a, button, div, i, span

from pindb.database.message import Message
from pindb.templates.messages.render import (
    message_target_url,
    message_title,
    message_visual,
    render_message_body,
)

Tab = Literal["inbox", "archived"]

# (message, is_unread) — read state is joined in by the caller, never lazy-loaded.
MessageRow = tuple[Message, bool]

_TITLE_CLASS = (
    "text-left bg-transparent border-0 p-0 font-inherit cursor-pointer "
    "font-medium text-base-text hover:text-accent"
)
_ARCHIVE_CLASS = (
    "shrink-0 inline-flex items-center justify-center p-1.5 rounded border "
    "border-lightest bg-main text-lightest-hover hover:text-accent hover:border-accent "
    "cursor-pointer"
)


def _row_dot(is_unread: bool) -> Element:
    """Filled dot when unread, hollow ring when read."""
    state = "bg-accent" if is_unread else "border border-lightest"
    return span(
        class_=f"shrink-0 mt-1.5 w-2.5 h-2.5 rounded-full {state}",
        aria_hidden="true",
    )


def _archive_control(request: Request, message_id: int, tab: Tab) -> Element:
    if tab == "archived":
        url = str(request.url_for("unarchive_message", message_id=message_id))
        icon, label = "archive-restore", "Unarchive"
    else:
        url = str(request.url_for("archive_message", message_id=message_id))
        icon, label = "archive", "Archive"
    return button(
        type="button",
        hx_post=url,
        hx_target=f"#message-row-{message_id}",
        hx_swap="outerHTML",
        title=label,
        aria_label=label,
        class_=_ARCHIVE_CLASS,
    )[i(data_lucide=icon, class_="w-4 h-4", aria_hidden="true")]


def message_row(
    request: Request,
    message: Message,
    *,
    is_unread: bool,
    tab: Tab,
    compact: bool = False,
) -> Element:
    """One message: unread dot, visual, clickable title, body, archive control.

    Clicking the title POSTs ``/messages/{id}/read`` and swaps this row. When the
    message resolves a target URL the title is also a real link and the read
    endpoint replies with ``HX-Redirect`` so the click navigates; otherwise the
    body simply stays visible inline.
    """
    row_id = f"message-row-{message.id}"
    read_url = str(
        request.url_for(
            "mark_message_read", message_id=message.id
        ).include_query_params(tab=tab, compact=int(compact))
    )
    target_url = message_target_url(request, message)
    title = message_title(message.body)

    swap_attrs: dict[str, object] = {
        "hx_post": read_url,
        "hx_target": f"#{row_id}",
        "hx_swap": "outerHTML",
    }
    title_el: Element = (
        a(href=target_url, class_=f"{_TITLE_CLASS} no-underline", **swap_attrs)[title]
        if target_url
        else button(type="button", class_=_TITLE_CLASS, **swap_attrs)[title]
    )

    body_el = (
        None
        if compact
        else div(class_="text-sm text-lightest-hover mt-1 markdown-content")[
            render_message_body(message.body)
        ]
    )

    return div(
        id=row_id,
        class_="flex items-start gap-3 p-3 rounded-lg border border-lightest bg-main",
    )[
        _row_dot(is_unread),
        span(class_="shrink-0 mt-0.5")[message_visual(message.body)],
        div(class_="min-w-0 flex-1")[title_el, body_el],
        _archive_control(request, message.id, tab),
    ]


def mark_all_read_button(request: Request, *, target: str) -> Element:
    """ "Mark all as read" — posts to ``/messages/read-all`` and swaps *target*."""
    return button(
        type="button",
        hx_post=str(request.url_for("mark_all_messages_read")),
        hx_target=f"#{target}",
        hx_swap="outerHTML",
        class_=(
            "w-full text-sm text-accent bg-transparent border-0 py-1 rounded "
            "cursor-pointer hover:bg-lighter-hover"
        ),
    )["Mark all as read"]
