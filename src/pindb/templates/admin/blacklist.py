"""Admin page for the do-not-index name blacklist (Shops/Artists).

Card list rather than a table: entries are few, and each carries a free-text
reason that wraps badly in a column.
"""

from __future__ import annotations

from typing import Sequence

from fastapi import Request
from htpy import (
    Element,
    button,
    div,
    form,
    hr,
    input,
    label,
    option,
    p,
    select,
    span,
)

from pindb.database.blacklist import BlacklistedName, BlacklistEntityType
from pindb.templates.base import html_base
from pindb.templates.components.display.empty_state import empty_state
from pindb.templates.components.layout.centered import centered_div
from pindb.templates.components.layout.page_heading import page_heading

_TYPE_LABELS: dict[BlacklistEntityType, str] = {
    BlacklistEntityType.shop: "Shop",
    BlacklistEntityType.artist: "Artist",
}


def _add_form(*, request: Request) -> Element:
    return form(
        method="post",
        action=str(request.url_for("post_admin_blacklist_add")),
        class_="flex flex-col gap-2 rounded-lg border border-lightest p-4",
    )[
        p(class_="font-semibold")["Add a name"],
        div(class_="flex flex-wrap items-end gap-2")[
            div(class_="flex flex-col gap-1 grow min-w-48")[
                label(for_="blacklist-name", class_="text-sm font-semibold")[
                    "Name", span(class_="text-error-main ml-0.5")["*"]
                ],
                input(
                    type="text",
                    name="name",
                    id="blacklist-name",
                    required=True,
                    autocomplete="off",
                ),
            ],
            div(class_="flex flex-col gap-1")[
                label(for_="blacklist-entity-type", class_="text-sm font-semibold")[
                    "Applies to"
                ],
                select(
                    name="entity_type",
                    id="blacklist-entity-type",
                )[
                    option(value="shop")["Shop"],
                    option(value="artist")["Artist"],
                    option(value="both")["Both"],
                ],
            ],
            div(class_="flex flex-col gap-1 grow min-w-48")[
                label(for_="blacklist-reason", class_="text-sm font-semibold")[
                    "Note (admin-only)"
                ],
                input(
                    type="text",
                    name="reason",
                    id="blacklist-reason",
                    autocomplete="off",
                    placeholder="e.g. requested removal via email, 2026-07-01",
                ),
            ],
            button(
                type="submit",
                class_="btn btn-primary cursor-pointer",
            )["Add"],
        ],
        p(class_="text-sm text-lightest-hover")[
            "Add one row per known spelling or alias. Exact matches are blocked "
            "at submission; similar names only warn the editor."
        ],
    ]


def _entry_card(*, request: Request, entry: BlacklistedName) -> Element:
    return div(
        class_="flex flex-wrap items-center gap-3 rounded-lg border border-lightest p-3"
    )[
        span(
            class_="text-xs font-semibold px-2 py-0.5 rounded bg-lightest "
            "text-base-text"
        )[_TYPE_LABELS[entry.entity_type]],
        span(class_="font-medium wrap-break-word")[entry.name],
        entry.reason
        and span(class_="text-sm text-lightest-hover wrap-break-word grow")[
            entry.reason
        ],
        span(class_="text-xs text-lightest-hover ml-auto")[
            f"added {entry.created_at:%Y-%m-%d}"
        ],
        form(
            method="post",
            action=str(
                request.url_for("post_admin_blacklist_delete", entry_id=entry.id)
            ),
        )[
            button(
                type="submit",
                class_="btn btn-danger cursor-pointer text-sm",
            )["Remove"]
        ],
    ]


def admin_blacklist_page(
    *,
    request: Request,
    entries: Sequence[BlacklistedName],
) -> Element:
    return html_base(
        title="Name Blacklist",
        request=request,
        body_content=centered_div(
            content=[
                page_heading(icon="ban", text="Name Blacklist"),
                p(class_="text-sm")[
                    "Shops and artists listed here asked not to be cataloged. "
                    "Creating or renaming an entity to an exact match is refused "
                    "with “not indexable at their request”; similar names show "
                    "the editor a warning before submission."
                ],
                hr,
                _add_form(request=request),
                div(class_="flex flex-col gap-2")[
                    [_entry_card(request=request, entry=entry) for entry in entries]
                    if entries
                    else empty_state("No blacklisted names.")
                ],
            ],
            flex=True,
            col=True,
        ),
    )
