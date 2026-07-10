"""
htpy fragment builder: `templates/components/display/pending_changes_table.py`.
"""

from collections.abc import Sequence

from htpy import Element, div, i, table, tbody, td, th, thead, tr

from pindb.database.pending_edit_utils import PendingChange


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
                    tr(class_="border-b border-lightest text-left text-lightest-hover")[
                        th(class_="px-4 py-2 font-medium")["Field"],
                        th(class_="px-4 py-2 font-medium")["Before"],
                        th(class_="px-4 py-2 font-medium")["After"],
                    ]
                ],
                tbody[
                    [
                        tr(class_="border-b border-lightest last:border-0 align-top")[
                            td(class_="px-4 py-2 font-medium text-base-text")[
                                change.label
                            ],
                            td(
                                class_="px-4 py-2 text-lightest-hover whitespace-pre-wrap break-words"
                            )[change.old],
                            td(
                                class_="px-4 py-2 text-base-text whitespace-pre-wrap break-words"
                            )[change.new],
                        ]
                        for change in changes
                    ]
                ],
            ]
        ],
    ]
