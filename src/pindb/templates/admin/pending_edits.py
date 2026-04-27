"""
Pending admin page section for proposed edits.
"""

from collections.abc import Callable
from datetime import datetime

from htpy import (
    Element,
    a,
    button,
    div,
    form,
    h2,
    i,
    p,
    span,
    table,
    tbody,
    td,
    th,
    thead,
    tr,
)
from titlecase import titlecase

from pindb.database.entity_type import EntityType
from pindb.database.pending_edit import PendingEdit
from pindb.database.pending_mixin import PendingAuditEntity
from pindb.database.user import User
from pindb.templates.list.base import TABLE_LIST_SCROLL


def _edit_groups_section(
    *,
    edit_groups: dict[tuple[str, int], list[PendingEdit]],
    entities: dict[tuple[str, int], PendingAuditEntity],
    creators: dict[int, User],
    local_date_formatter: Callable[[datetime | None], Element | str],
) -> Element:
    return div(class_="flex flex-col gap-2")[
        div(class_="flex items-baseline gap-2")[
            i(data_lucide="pen", class_="inline-block w-4 h-4"),
            h2["Pending Edits"],
            span(
                class_="text-xs font-semibold px-2 py-0.5 rounded bg-darker text-lightest-hover"
            )[str(len(edit_groups))],
        ],
        p(class_="text-lightest-hover text-sm")[
            "Edits proposed by editors to approved entries. "
            "Approving applies the accumulated chain to the canonical entry."
        ],
        div(class_=TABLE_LIST_SCROLL)[
            table(class_="w-full text-sm")[
                thead[
                    tr(class_="text-left text-lightest-hover border-b border-darker")[
                        th(class_="py-2 pr-6 font-medium")["Entity"],
                        th(class_="py-2 pr-6 font-medium")["Edits"],
                        th(class_="py-2 pr-6 font-medium")["Latest editor"],
                        th(class_="py-2 pr-6 font-medium")["Latest at"],
                        th(class_="py-2 font-medium")["Actions"],
                    ]
                ],
                tbody[
                    [
                        _edit_group_row(
                            table_name=table_name,
                            entity_id=entity_id,
                            chain=chain,
                            entity=entities.get((table_name, entity_id)),
                            creators=creators,
                            local_date_formatter=local_date_formatter,
                        )
                        for (table_name, entity_id), chain in sorted(
                            edit_groups.items(),
                            key=lambda group_entry: (
                                group_entry[0][0],
                                group_entry[0][1],
                            ),
                        )
                    ]
                ],
            ],
        ],
    ]


def _edit_group_row(
    *,
    table_name: str,
    entity_id: int,
    chain: list[PendingEdit],
    entity: PendingAuditEntity | None,
    creators: dict[int, User],
    local_date_formatter: Callable[[datetime | None], Element | str],
) -> Element:
    entity_type = EntityType.from_table_name(table_name)
    slug: str = entity_type.slug if entity_type is not None else table_name
    name: str = getattr(entity, "name", f"#{entity_id}") if entity else f"#{entity_id}"
    latest = chain[-1] if chain else None
    latest_editor: str = "—"
    latest_at: datetime | None = None
    if latest is not None:
        if latest.created_by_id and latest.created_by_id in creators:
            latest_editor = creators[latest.created_by_id].username
        if latest.created_at:
            latest_at = latest.created_at

    approve_url = f"/admin/pending/approve-edits/{slug}/{entity_id}"
    reject_url = f"/admin/pending/reject-edits/{slug}/{entity_id}"
    delete_url = f"/admin/pending/delete-edits/{slug}/{entity_id}"
    pending_view_url = f"/get/{slug}/{entity_id}?version=pending"

    return tr(class_="border-b border-darker hover:bg-main-hover")[
        td(class_="py-2 pr-6")[
            a(href=pending_view_url)[name],
            span(class_="block text-xs text-lighter-hover")[
                f"{titlecase(slug.replace('_', ' '))}"
            ],
        ],
        td(class_="py-2 pr-6")[str(len(chain))],
        td(class_="py-2 pr-6 text-lighter-hover")[latest_editor],
        td(class_="py-2 pr-6 text-lighter-hover")[local_date_formatter(latest_at)],
        td(class_="py-2")[
            div(class_="flex gap-2")[
                form(method="post", action=approve_url)[
                    button(
                        type="submit",
                        class_="btn btn-sm btn-primary",
                        title="Approve edits",
                    )[
                        i(data_lucide="check", class_="inline-block w-3 h-3 mr-1"),
                        "Approve",
                    ]
                ],
                form(method="post", action=reject_url)[
                    button(
                        type="submit",
                        class_="btn btn-sm btn-warning",
                        title="Reject edits",
                    )[
                        i(data_lucide="x", class_="inline-block w-3 h-3 mr-1"),
                        "Reject",
                    ]
                ],
                form(method="post", action=delete_url)[
                    button(
                        type="submit",
                        class_="btn btn-sm btn-error",
                        title="Delete edits",
                    )[
                        i(data_lucide="trash-2", class_="inline-block w-3 h-3 mr-1"),
                        "Delete",
                    ]
                ],
            ]
        ],
    ]
