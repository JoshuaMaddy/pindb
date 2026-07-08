"""Shared htpy components for the admin pending-approval sections.

Approve/reject/delete buttons, the count badge, section headers, and the
scrolling table header are identical across the pending entity/edit/bulk
sections; defining them once keeps styling and action wiring in sync.
"""

from collections.abc import Sequence

from htpy import Element, button, div, form, h2, i, span, table, tbody, th, thead, tr

from pindb.templates.list.base import TABLE_LIST_SCROLL

# action key -> (lucide icon, button variant class, default label)
_ACTION_SPECS: dict[str, tuple[str, str, str]] = {
    "approve": ("check", "btn-primary", "Approve"),
    "reject": ("x", "btn-warning", "Reject"),
    "delete": ("trash-2", "btn-error", "Delete"),
}


def action_form_button(
    *, action: str, url: str, label: str | None = None, title: str | None = None
) -> Element:
    """A single POST form wrapping an icon button for an approve/reject/delete action.

    ``hx-post`` swaps the whole ``#pending-content`` region in place so the queue
    updates without a full-page reload (which would reset the scroll position).
    ``method``/``action`` remain as a no-JS fallback that redirects to the page.
    """
    icon, variant, default_label = _ACTION_SPECS[action]
    text = label or default_label
    return form(
        method="post",
        action=url,
        hx_post=url,
        hx_target="#pending-content",
        hx_swap="outerHTML",
    )[
        button(type="submit", class_=f"btn btn-sm {variant}", title=title or text)[
            i(data_lucide=icon, class_="inline-block w-3 h-3 mr-1"),
            text,
        ]
    ]


def action_buttons(*buttons: Element) -> Element:
    """Horizontal row wrapping the action buttons for one pending row/card."""
    return div(class_="flex gap-2")[list(buttons)]


def count_badge(count: int) -> Element:
    """Small pill showing a pending count next to a section heading."""
    return span(
        class_="text-xs font-semibold px-2 py-0.5 rounded bg-darker text-lightest-hover"
    )[str(count)]


def section_header(*, icon: str, title: str, count: int) -> Element:
    """``icon + <h2> + count badge`` row shared by every pending section."""
    return div(class_="flex items-baseline gap-2")[
        i(data_lucide=icon, class_="inline-block w-4 h-4"),
        h2[title],
        count_badge(count),
    ]


def pending_table(*, columns: Sequence[str], rows: Sequence[Element]) -> Element:
    """Scroll-wrapped table; every column but the last gets right padding, and
    the last column (Actions) is flush, matching the original markup."""
    return div(class_=TABLE_LIST_SCROLL)[
        table(class_="w-full text-sm")[
            thead[
                tr(class_="text-left text-lightest-hover border-b border-darker")[
                    [
                        th(class_="py-2 pr-6 font-medium")[label]
                        for label in columns[:-1]
                    ],
                    th(class_="py-2 font-medium")[columns[-1]],
                ]
            ],
            tbody[list(rows)],
        ]
    ]
