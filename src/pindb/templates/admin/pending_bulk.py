"""
Pending admin page section for bulk submission bundles.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID

from htpy import Element, a, button, div, form, h2, h3, i, span

from pindb.database.entity_type import EntityType
from pindb.database.pending_edit import PendingEdit
from pindb.database.pending_mixin import PendingAuditEntity


@dataclass
class BulkGroupView:
    """Display-time bundle of every pending row that shares a ``bulk_id``."""

    bulk_id: UUID
    entities: list[tuple[str, PendingAuditEntity]] = field(default_factory=list)
    edits: list[tuple[tuple[str, int], list[PendingEdit]]] = field(default_factory=list)
    edit_entities: dict[tuple[str, int], PendingAuditEntity] = field(
        default_factory=dict
    )


def _bulk_groups_section(*, bulk_groups: Sequence[BulkGroupView]) -> Element:
    return div(class_="flex flex-col gap-4")[
        div(class_="flex items-baseline gap-2")[
            i(data_lucide="layers", class_="inline-block w-4 h-4"),
            h2["Bulk Bundles"],
            span(class_="text-xs font-semibold px-2 py-0.5 rounded")[
                str(len(bulk_groups))
            ],
        ],
        div(class_="flex flex-col gap-3")[
            [_bulk_group_card(group=group) for group in bulk_groups]
        ],
    ]


def _bulk_group_card(*, group: BulkGroupView) -> Element:
    entity_count = len(group.entities)
    edit_count = sum(len(chain) for _key, chain in group.edits)
    if entity_count and not edit_count:
        kind = "create"
    elif edit_count and not entity_count:
        kind = "edit"
    else:
        kind = "mixed"
    summary_parts: list[str] = []
    if entity_count:
        summary_parts.append(f"{entity_count} new item(s)")
    if edit_count:
        summary_parts.append(f"{edit_count} pending edit(s)")
    summary = ", ".join(summary_parts) or "empty"

    approve_url = f"/admin/pending/approve-bulk/{group.bulk_id}"
    reject_url = f"/admin/pending/reject-bulk/{group.bulk_id}"
    delete_url = f"/admin/pending/delete-bulk/{group.bulk_id}"

    return div(class_="rounded border border-lightest p-4 flex flex-col gap-3")[
        div(class_="flex items-center gap-2 flex-wrap")[
            i(data_lucide="layers", class_="inline-block w-4 h-4"),
            h3(class_="font-semibold")[f"Bulk {kind}"],
            span(class_="text-xs")[f"({summary})"],
            span(class_="text-xs ml-auto font-mono")[str(group.bulk_id)],
        ],
        group.entities
        and div(class_="flex flex-col gap-1")[
            span(class_="text-xs")["New items"],
            *[
                div(class_="flex items-baseline gap-2 text-sm")[
                    span(class_="text-lighter w-20")[entity_type_slug],
                    a(
                        href=f"/get/{entity_type_slug}/{entity.id}",
                        class_="text-lightest hover:text-accent",
                    )[getattr(entity, "name", f"#{entity.id}")],
                ]
                for entity_type_slug, entity in group.entities
            ],
        ],
        group.edits
        and div(class_="flex flex-col gap-1")[
            span(class_="text-xs")["Edits"],
            *[
                _bulk_edit_row(
                    table_name=table_name,
                    entity_id=entity_id,
                    chain=chain,
                    entity=group.edit_entities.get((table_name, entity_id)),
                )
                for (table_name, entity_id), chain in group.edits
            ],
        ],
        div(class_="flex gap-2")[
            form(method="post", action=approve_url)[
                button(type="submit", class_="btn btn-sm btn-primary")[
                    i(data_lucide="check", class_="inline-block w-3 h-3 mr-1"),
                    "Approve bundle",
                ]
            ],
            form(method="post", action=reject_url)[
                button(type="submit", class_="btn btn-sm btn-warning")[
                    i(data_lucide="x", class_="inline-block w-3 h-3 mr-1"),
                    "Reject bundle",
                ]
            ],
            form(method="post", action=delete_url)[
                button(type="submit", class_="btn btn-sm btn-error")[
                    i(data_lucide="trash-2", class_="inline-block w-3 h-3 mr-1"),
                    "Delete bundle",
                ]
            ],
        ],
    ]


def _bulk_edit_row(
    *,
    table_name: str,
    entity_id: int,
    chain: list[PendingEdit],
    entity: PendingAuditEntity | None,
) -> Element:
    entity_type = EntityType.from_table_name(table_name)
    slug: str = entity_type.slug if entity_type is not None else table_name
    name: str = getattr(entity, "name", f"#{entity_id}") if entity else f"#{entity_id}"
    return div(class_="flex items-baseline gap-2 text-sm")[
        span(class_="text-lighter-hover w-20")[slug],
        a(href=f"/get/{slug}/{entity_id}?version=pending", class_="hover:text-accent")[
            name
        ],
        span(class_="text-xs text-lighter-hover")[f"({len(chain)} edit(s))"],
    ]
