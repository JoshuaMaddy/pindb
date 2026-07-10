"""Navbar messages widget: the mail icon (with unread dot) plus a desktop
hover-preview panel showing the newest few messages. Reads the preview data
stashed on ``request.state`` by the auth middleware.
"""

from __future__ import annotations

from fastapi import Request
from htpy import Element, a, div, i, span

from pindb.templates.components.display.empty_state import empty_state
from pindb.templates.messages.components import (
    MessageRow,
    mark_all_read_button,
    message_row,
)
from pindb.templates.messages.nav_indicator import unread_dot

PREVIEW_ID = "messages-preview"
PREVIEW_LIMIT = 5


def messages_preview(
    request: Request,
    rows: list[MessageRow],
    *,
    unread_exists: bool,
) -> Element:
    """The hover panel body (swap target ``#messages-preview``)."""
    return div(class_="flex flex-col gap-1 w-80 max-w-[90vw]", id=PREVIEW_ID)[
        div(class_="flex items-center justify-between px-1 pb-1")[
            span(class_="font-semibold text-sm")["Messages"],
            a(
                href="/messages",
                class_="text-xs text-accent no-underline hover:underline",
            )["View all"],
        ],
        div(class_="flex flex-col gap-1")[
            [
                message_row(
                    request, message, is_unread=is_unread, tab="inbox", compact=True
                )
                for message, is_unread in rows
            ]
            if rows
            else empty_state("No messages.", small=True)
        ],
        unread_exists
        and div(class_="border-t border-lightest mt-1 pt-1")[
            mark_all_read_button(request, target=PREVIEW_ID)
        ],
    ]


def messages_nav_widget(request: Request) -> Element:
    """Mail icon + unread dot, with a desktop-only hover preview panel.

    The panel is a descendant of the ``group`` and offset via ``pt-2`` **padding**
    (not margin) so the cursor never leaves the hover region crossing the gap, and
    HTMX swaps inside the panel keep it open. On mobile the panel never shows
    (``sm:group-hover:``), so tapping the icon simply navigates to ``/messages``.
    """
    unread_count: int = getattr(request.state, "unread_message_count", 0) or 0
    rows: list[MessageRow] = getattr(request.state, "message_preview", []) or []
    unread_exists = unread_count > 0

    return div(class_="relative group")[
        a(
            href="/messages",
            aria_label="Messages",
            class_="relative inline-flex items-center text-base-text hover:text-accent no-underline",
        )[
            i(data_lucide="mail", class_="w-5 h-5"),
            unread_dot(unread_exists),
        ],
        div(
            class_=(
                "absolute right-0 top-full pt-2 z-30 hidden "
                "sm:group-hover:block sm:group-focus-within:block"
            )
        )[
            div(class_="bg-main border border-lightest rounded-lg shadow-lg p-2")[
                messages_preview(request, rows, unread_exists=unread_exists)
            ]
        ],
    ]
