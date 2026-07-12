"""Shared htpy components for the admin pending-approval sections.

The count badge, section headers, and the scrolling table header are identical
across the pending entity/edit/bulk sections; defining them once keeps styling in
sync. The approve/reject/delete buttons themselves live in
``components/display/review_actions.py`` — the entity detail pages render the same
three actions — and are re-exported here for the queue sections.
"""

from collections.abc import Sequence

from htpy import (
    Element,
    col,
    colgroup,
    div,
    h2,
    i,
    span,
    table,
    tbody,
    th,
    thead,
    tr,
)

from pindb.templates.components.display.review_actions import (
    action_buttons,
    action_form_button,
    request_changes_button,
)
from pindb.templates.list.base import TABLE_LIST_SCROLL

__all__ = [
    "action_buttons",
    "action_form_button",
    "count_badge",
    "pending_table",
    "request_changes_button",
    "section_header",
]


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


def pending_table(
    *,
    columns: Sequence[str],
    rows: Sequence[Element],
    col_widths: Sequence[str | None] | None = None,
) -> Element:
    """Scroll-wrapped table; every column but the last gets right padding, and
    the last column (Actions) is flush, matching the original markup.

    When ``col_widths`` is given (one entry per column, ``None`` = flexible), the
    table switches to a fixed layout with a ``<colgroup>`` so that separate
    tables sharing the same widths line their columns up vertically. Used by the
    per-entity pending sections (pins/shops/artists/tags/pin sets) so their
    Name/Submitted-by/Submitted-at/Actions columns align across sections.
    """
    table_class = "w-full text-sm"
    colgroup_el: Element | str = ""
    if col_widths is not None:
        table_class = "w-full min-w-[45rem] table-fixed text-sm"
        colgroup_el = colgroup[
            [col(style=f"width:{w}") if w else col for w in col_widths]
        ]
    return div(class_=TABLE_LIST_SCROLL)[
        table(class_=table_class)[
            colgroup_el,
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
