"""
htpy page and fragment builders: `templates/admin/pending.py`.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Sequence
from uuid import UUID

from fastapi import Request
from htpy import (
    Element,
    VoidElement,
    a,
    button,
    div,
    form,
    h2,
    h3,
    hr,
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

from pindb.database.artist import Artist
from pindb.database.entity_type import EntityType
from pindb.database.pending_edit import PendingEdit
from pindb.database.pending_mixin import PendingAuditEntity
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.database.tag import Tag
from pindb.database.user import User
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div
from pindb.templates.components.page_heading import page_heading
from pindb.templates.list.base import TABLE_LIST_SCROLL


@dataclass
class BulkGroupView:
    """Display-time bundle of every pending row that shares a ``bulk_id``."""

    bulk_id: UUID
    entities: list[tuple[str, PendingAuditEntity]] = field(default_factory=list)
    edits: list[tuple[tuple[str, int], list[PendingEdit]]] = field(default_factory=list)
    edit_entities: dict[tuple[str, int], PendingAuditEntity] = field(
        default_factory=dict
    )


def pending_page(
    request: Request,
    pending_pins: list[Pin],
    pending_shops: list[Shop],
    pending_artists: list[Artist],
    pending_tags: list[Tag],
    pending_pin_sets: list[PinSet],
    creators: dict[int, User],
    edit_groups: dict[tuple[str, int], list[PendingEdit]] | None = None,
    edit_group_entities: dict[tuple[str, int], PendingAuditEntity] | None = None,
    bulk_groups: Sequence[BulkGroupView] | None = None,
) -> Element:
    edit_groups = edit_groups or {}
    edit_group_entities = edit_group_entities or {}
    bulk_groups = bulk_groups or []
    total = (
        len(pending_pins)
        + len(pending_shops)
        + len(pending_artists)
        + len(pending_tags)
        + len(pending_pin_sets)
        + len(edit_groups)
        + len(bulk_groups)
    )

    return html_base(
        title="Pending Approvals",
        request=request,
        body_content=centered_div(
            content=[
                div(class_="flex items-baseline gap-3")[
                    page_heading(icon="clock", text="Pending Approvals"),
                    span(
                        class_="text-xs font-semibold px-2 py-0.5 rounded bg-amber-700 text-amber-100"
                    )[str(total)],
                ],
                p(class_="text-pin-base-300 text-sm")[
                    "Review and approve or reject pending entries submitted by editors. "
                    "Approving a pin also approves its pending dependencies (shops, artists, tags)."
                ],
                hr,
                *_sections(
                    request,
                    pending_pins,
                    pending_shops,
                    pending_artists,
                    pending_tags,
                    pending_pin_sets,
                    creators,
                    edit_groups,
                    edit_group_entities,
                    bulk_groups,
                ),
            ],
            flex=True,
            col=True,
        ),
    )


def _sections(
    request: Request,
    pending_pins: list[Pin],
    pending_shops: list[Shop],
    pending_artists: list[Artist],
    pending_tags: list[Tag],
    pending_pin_sets: list[PinSet],
    creators: dict[int, User],
    edit_groups: dict[tuple[str, int], list[PendingEdit]],
    edit_group_entities: dict[tuple[str, int], PendingAuditEntity],
    bulk_groups: Sequence[BulkGroupView],
) -> list[Element | VoidElement]:
    sections: list[Element | VoidElement] = []

    def _add(
        label: str, icon: str, entity_type: str, items: Sequence[PendingAuditEntity]
    ) -> None:
        if items:
            sections.append(
                _entity_section(
                    label=label,
                    icon=icon,
                    entity_type=entity_type,
                    items=items,
                    creators=creators,
                )
            )
            sections.append(hr)

    _add(
        label="Pins",
        icon="pin",
        entity_type="pin",
        items=pending_pins,
    )
    _add(
        label="Shops",
        icon="store",
        entity_type="shop",
        items=pending_shops,
    )
    _add(
        label="Artists",
        icon="palette",
        entity_type="artist",
        items=pending_artists,
    )
    _add(
        label="Tags",
        icon="tag",
        entity_type="tag",
        items=pending_tags,
    )
    _add(
        label="Pin Sets",
        icon="library",
        entity_type="pin_set",
        items=pending_pin_sets,
    )

    if edit_groups:
        sections.append(
            _edit_groups_section(
                edit_groups=edit_groups,
                entities=edit_group_entities,
                creators=creators,
            )
        )
        sections.append(hr)

    if bulk_groups:
        sections.append(_bulk_groups_section(bulk_groups=bulk_groups))
        sections.append(hr)

    if not sections:
        sections.append(
            div(class_="text-pin-base-300 text-center py-8")[
                i(data_lucide="check-circle", class_="inline-block w-8 h-8 mb-2"),
                p["No pending entries. All clear."],
            ]
        )

    return sections


def _entity_section(
    label: str,
    icon: str,
    entity_type: str,
    items: Sequence[PendingAuditEntity],
    creators: dict[int, User],
) -> Element:
    return div(class_="flex flex-col gap-2")[
        div(class_="flex items-baseline gap-2")[
            i(data_lucide=icon, class_="inline-block w-4 h-4"),
            h2[label],
            span(
                class_="text-xs font-semibold px-2 py-0.5 rounded bg-pin-base-700 text-pin-base-300"
            )[str(len(items))],
        ],
        div(class_=TABLE_LIST_SCROLL)[
            table(class_="w-full text-sm")[
                thead[
                    tr(
                        class_="text-left text-pin-base-300 border-b border-pin-base-700"
                    )[
                        th(class_="py-2 pr-6 font-medium")["Name"],
                        th(class_="py-2 pr-6 font-medium")["Submitted by"],
                        th(class_="py-2 pr-6 font-medium")["Submitted at"],
                        th(class_="py-2 font-medium")["Actions"],
                    ]
                ],
                tbody[
                    [
                        _entity_row(
                            entity_type=entity_type,
                            entity=item,
                            creators=creators,
                        )
                        for item in items
                    ]
                ],
            ],
        ],
    ]


def _entity_row(
    entity_type: str,
    entity: PendingAuditEntity,
    creators: dict[int, User],
) -> Element:
    name: str = getattr(entity, "name", f"#{entity.id}")
    creator: User | None = (
        creators.get(entity.created_by_id) if entity.created_by_id else None
    )
    creator_name: str = creator.username if creator else "â€”"
    created_at: datetime | None = entity.created_at
    created_str: str = created_at.strftime("%Y-%m-%d %H:%M") if created_at else "â€”"

    approve_url = f"/admin/pending/approve/{entity_type}/{entity.id}"
    reject_url = f"/admin/pending/reject/{entity_type}/{entity.id}"
    delete_url = f"/admin/pending/delete/{entity_type}/{entity.id}"

    # Show pending dependencies for pins
    dep_note: Element | str = ""
    if entity_type == "pin" and isinstance(entity, Pin):
        pending_deps = (
            [shop.name for shop in entity.shops if shop.is_pending]
            + [artist.name for artist in entity.artists if artist.is_pending]
            + [tag.display_name for tag in entity.tags if tag.is_pending]
        )
        if pending_deps:
            dep_note = span(class_="block text-xs text-amber-400 mt-0.5")[
                "Will also approve: " + ", ".join(pending_deps)
            ]

    return tr(class_="border-b border-pin-base-800 hover:bg-pin-base-500")[
        td(class_="py-2 pr-6")[
            a(href=f"/get/{entity_type}/{entity.id}")[name],
            dep_note,
        ],
        td(class_="py-2 pr-6 text-pin-base-400")[creator_name],
        td(class_="py-2 pr-6 text-pin-base-400")[created_str],
        td(class_="py-2")[
            div(class_="flex gap-2")[
                form(method="post", action=approve_url)[
                    button(
                        type="submit",
                        class_="btn btn-sm btn-primary",
                        title="Approve",
                    )[
                        i(data_lucide="check", class_="inline-block w-3 h-3 mr-1"),
                        "Approve",
                    ]
                ],
                form(method="post", action=reject_url)[
                    button(
                        type="submit",
                        class_="btn btn-sm btn-warning",
                        title="Reject",
                    )[
                        i(data_lucide="x", class_="inline-block w-3 h-3 mr-1"),
                        "Reject",
                    ]
                ],
                form(method="post", action=delete_url)[
                    button(
                        type="submit",
                        class_="btn btn-sm btn-error",
                        title="Delete",
                    )[
                        i(data_lucide="trash-2", class_="inline-block w-3 h-3 mr-1"),
                        "Delete",
                    ]
                ],
            ]
        ],
    ]


def _edit_groups_section(
    edit_groups: dict[tuple[str, int], list[PendingEdit]],
    entities: dict[tuple[str, int], PendingAuditEntity],
    creators: dict[int, User],
) -> Element:
    return div(class_="flex flex-col gap-2")[
        div(class_="flex items-baseline gap-2")[
            i(data_lucide="pen", class_="inline-block w-4 h-4"),
            h2["Pending Edits"],
            span(
                class_="text-xs font-semibold px-2 py-0.5 rounded bg-pin-base-700 text-pin-base-300"
            )[str(len(edit_groups))],
        ],
        p(class_="text-pin-base-300 text-sm")[
            "Edits proposed by editors to approved entries. "
            "Approving applies the accumulated chain to the canonical entry."
        ],
        div(class_=TABLE_LIST_SCROLL)[
            table(class_="w-full text-sm")[
                thead[
                    tr(
                        class_="text-left text-pin-base-300 border-b border-pin-base-700"
                    )[
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
    table_name: str,
    entity_id: int,
    chain: list[PendingEdit],
    entity: PendingAuditEntity | None,
    creators: dict[int, User],
) -> Element:
    entity_type = EntityType.from_table_name(table_name)
    slug: str = entity_type.slug if entity_type is not None else table_name
    name: str = getattr(entity, "name", f"#{entity_id}") if entity else f"#{entity_id}"
    latest = chain[-1] if chain else None
    latest_editor: str = "â€”"
    latest_at: str = "â€”"
    if latest is not None:
        if latest.created_by_id and latest.created_by_id in creators:
            latest_editor = creators[latest.created_by_id].username
        if latest.created_at:
            latest_at = latest.created_at.strftime("%Y-%m-%d %H:%M")

    approve_url = f"/admin/pending/approve-edits/{slug}/{entity_id}"
    reject_url = f"/admin/pending/reject-edits/{slug}/{entity_id}"
    delete_url = f"/admin/pending/delete-edits/{slug}/{entity_id}"
    pending_view_url = f"/get/{slug}/{entity_id}?version=pending"

    return tr(class_="border-b border-pin-base-800 hover:bg-pin-base-500")[
        td(class_="py-2 pr-6")[
            a(href=pending_view_url)[name],
            span(class_="block text-xs text-pin-base-400")[
                f"{slug.replace('_', ' ').title()}"
            ],
        ],
        td(class_="py-2 pr-6")[str(len(chain))],
        td(class_="py-2 pr-6 text-pin-base-400")[latest_editor],
        td(class_="py-2 pr-6 text-pin-base-400")[latest_at],
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


def _bulk_groups_section(
    bulk_groups: Sequence[BulkGroupView],
) -> Element:
    return div(class_="flex flex-col gap-4")[
        div(class_="flex items-baseline gap-2")[
            i(data_lucide="layers", class_="inline-block w-4 h-4"),
            h2["Bulk Bundles"],
            span(
                class_="text-xs font-semibold px-2 py-0.5 rounded bg-pin-base-700 text-pin-base-300"
            )[str(len(bulk_groups))],
        ],
        p(class_="text-pin-base-300 text-sm")[
            "Pending items submitted together in a single bulk create or bulk edit. "
            "Approving, rejecting, or deleting operates on the whole bundle."
        ],
        div(class_="flex flex-col gap-3")[
            [_bulk_group_card(group=group) for group in bulk_groups]
        ],
    ]


def _bulk_group_card(group: BulkGroupView) -> Element:
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

    return div(
        class_="rounded border border-pin-border bg-pin-base-600 p-4 flex flex-col gap-3"
    )[
        div(class_="flex items-center gap-2 flex-wrap")[
            i(data_lucide="layers", class_="inline-block w-4 h-4"),
            h3(class_="font-semibold")[f"Bulk {kind}"],
            span(class_="text-xs text-pin-base-300")[f"({summary})"],
            span(class_="text-xs text-pin-base-400 ml-auto font-mono")[
                str(group.bulk_id)
            ],
        ],
        group.entities
        and div(class_="flex flex-col gap-1")[
            span(class_="text-xs text-pin-base-300")["New items"],
            *[
                div(class_="flex items-baseline gap-2 text-sm")[
                    span(class_="text-pin-base-400 w-20")[entity_type_slug],
                    a(
                        href=f"/get/{entity_type_slug}/{entity.id}",
                        class_="hover:text-accent",
                    )[getattr(entity, "name", f"#{entity.id}")],
                ]
                for entity_type_slug, entity in group.entities
            ],
        ],
        group.edits
        and div(class_="flex flex-col gap-1")[
            span(class_="text-xs text-pin-base-300")["Edits"],
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
                button(
                    type="submit",
                    class_="btn btn-sm btn-primary",
                )[
                    i(data_lucide="check", class_="inline-block w-3 h-3 mr-1"),
                    "Approve bundle",
                ]
            ],
            form(method="post", action=reject_url)[
                button(
                    type="submit",
                    class_="btn btn-sm btn-warning",
                )[
                    i(data_lucide="x", class_="inline-block w-3 h-3 mr-1"),
                    "Reject bundle",
                ]
            ],
            form(method="post", action=delete_url)[
                button(
                    type="submit",
                    class_="btn btn-sm btn-error",
                )[
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
        span(class_="text-pin-base-400 w-20")[slug],
        a(href=f"/get/{slug}/{entity_id}?version=pending", class_="hover:text-accent")[
            name
        ],
        span(class_="text-xs text-pin-base-400")[f"({len(chain)} edit(s))"],
    ]
