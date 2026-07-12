"""
Pending admin page section for proposed edits.
"""

from collections.abc import Callable
from datetime import datetime

from htpy import (
    Element,
    a,
    div,
    p,
    span,
    td,
    tr,
)

from pindb.database.entity_type import EntityType
from pindb.database.pending_edit import PendingEdit
from pindb.database.pending_mixin import PendingAuditEntity
from pindb.database.user import User
from pindb.templates.admin._pending_shared import (
    action_buttons,
    action_form_button,
    pending_table,
    request_changes_button,
    section_header,
)
from pindb.utils import pretty_titlecase


def _edit_groups_section(
    *,
    edit_groups: dict[tuple[str, int], list[PendingEdit]],
    entities: dict[tuple[str, int], PendingAuditEntity],
    creators: dict[int, User],
    local_date_formatter: Callable[[datetime | None], Element | str],
) -> Element:
    return div(class_="flex flex-col gap-2")[
        section_header(icon="pen", title="Pending Edits", count=len(edit_groups)),
        p(class_="text-lightest-hover text-sm")[
            "Edits proposed by editors to approved entries. "
            "Approving applies the accumulated chain to the canonical entry."
        ],
        pending_table(
            columns=["Entity", "Edits", "Latest editor", "Latest at", "Actions"],
            rows=[
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
            ],
        ),
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
                f"{pretty_titlecase(slug.replace('_', ' '))}"
            ],
        ],
        td(class_="py-2 pr-6")[str(len(chain))],
        td(class_="py-2 pr-6 text-lighter-hover")[latest_editor],
        td(class_="py-2 pr-6 text-lighter-hover")[local_date_formatter(latest_at)],
        td(class_="py-2")[
            action_buttons(
                action_form_button(
                    action="approve", url=approve_url, title="Approve edits"
                ),
                request_changes_button(
                    url=reject_url,
                    entity_label=f"the pending edits to {name}",
                    title="Request changes to these edits",
                ),
                action_form_button(
                    action="delete", url=delete_url, title="Delete edits"
                ),
            )
        ],
    ]
