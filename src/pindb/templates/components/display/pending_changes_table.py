"""
htpy fragment builder: `templates/components/display/pending_changes_table.py`.
"""

from collections.abc import Sequence

from htpy import Element, Node, div, i, li, table, tbody, td, th, thead, tr, ul

from pindb.database.pending_edit_utils import PendingChange

_CELL: str = "px-4 py-2 whitespace-pre-wrap break-words"
_HEAD: str = "px-4 py-2 font-medium text-lightest-hover"


def _delta_list(items: Sequence[str], sign: str, class_: str) -> Node:
    """Render one side of a list-field delta as signed entries, or an em dash.

    The color class goes on each ``li``, not the ``ul``: the base layer's
    ``* { @apply text-base-text }`` sets color on every element directly, so a
    color set on an ancestor is never inherited.
    """
    if not items:
        return "—"
    return ul(class_="space-y-0.5")[
        [li(class_=class_)[f"{sign} {item}"] for item in items]
    ]


def _change_row(change: PendingChange) -> Element:
    if change.is_delta:
        before: Node = _delta_list(change.removed, "−", "text-error-main")
        after: Node = _delta_list(change.added, "+", "text-success-main")
    else:
        before = change.old
        after = change.new
    return tr(class_="border-b border-lightest last:border-0 align-top")[
        td(class_="px-4 py-2 font-medium text-base-text")[change.label],
        td(class_=f"{_CELL} text-lightest-hover")[before],
        td(class_=f"{_CELL} text-base-text")[after],
    ]


def pending_changes_table(changes: Sequence[PendingChange]) -> Element | None:
    """Reviewer table of proposed field changes on the pending edit view."""
    if not changes:
        return None
    return div(class_="my-2 rounded border border-pending-dark overflow-hidden")[
        div(
            class_="bg-pending-dark text-pending-main px-4 py-2 text-sm font-medium flex items-center gap-2"
        )[
            i(
                data_lucide="list",
                class_="inline-block w-4 h-4",
                aria_hidden="true",
            ),
            "Proposed changes",
        ],
        div(class_="overflow-x-auto")[
            table(class_="w-full text-sm border-collapse")[
                thead[
                    tr(class_="border-b border-lightest text-left")[
                        th(class_=_HEAD)["Field"],
                        th(class_=_HEAD)["Before"],
                        th(class_=_HEAD)["After"],
                    ]
                ],
                tbody[[_change_row(change) for change in changes]],
            ]
        ],
    ]
