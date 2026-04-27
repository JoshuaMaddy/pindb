"""
Pending admin page sections for newly-created entities.
"""

from collections.abc import Callable, Sequence
from datetime import datetime

from htpy import (
    Element,
    VoidElement,
    a,
    button,
    div,
    form,
    h2,
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

from pindb.database.pending_edit import PendingEdit
from pindb.database.pending_mixin import PendingAuditEntity
from pindb.database.user import User
from pindb.templates.admin.pending_bulk import BulkGroupView
from pindb.templates.admin.pending_edits import _edit_groups_section
from pindb.templates.list.base import TABLE_LIST_SCROLL


def _sections(
    *,
    pending_pins: Sequence[PendingAuditEntity],
    pending_shops: Sequence[PendingAuditEntity],
    pending_artists: Sequence[PendingAuditEntity],
    pending_tags: Sequence[PendingAuditEntity],
    pending_pin_sets: Sequence[PendingAuditEntity],
    creators: dict[int, User],
    edit_groups: dict[tuple[str, int], list[PendingEdit]],
    edit_group_entities: dict[tuple[str, int], PendingAuditEntity],
    bulk_groups: Sequence[BulkGroupView],
    local_date_formatter: Callable[[datetime | None], Element | str],
    bulk_groups_section: Callable[..., Element],
) -> list[Element | VoidElement]:
    sections: list[Element | VoidElement] = []

    def _add(
        *,
        label: str,
        icon: str,
        entity_type: str,
        items: Sequence[PendingAuditEntity],
    ) -> None:
        if items:
            sections.append(
                _entity_section(
                    label=label,
                    icon=icon,
                    entity_type=entity_type,
                    items=items,
                    creators=creators,
                    local_date_formatter=local_date_formatter,
                )
            )
            sections.append(hr)

    _add(label="Pins", icon="pin", entity_type="pin", items=pending_pins)
    _add(label="Shops", icon="store", entity_type="shop", items=pending_shops)
    _add(label="Artists", icon="palette", entity_type="artist", items=pending_artists)
    _add(label="Tags", icon="tag", entity_type="tag", items=pending_tags)
    _add(
        label="Pin Sets", icon="library", entity_type="pin_set", items=pending_pin_sets
    )

    if edit_groups:
        sections.append(
            _edit_groups_section(
                edit_groups=edit_groups,
                entities=edit_group_entities,
                creators=creators,
                local_date_formatter=local_date_formatter,
            )
        )
        sections.append(hr)

    if bulk_groups:
        sections.append(bulk_groups_section(bulk_groups=bulk_groups))
        sections.append(hr)

    if not sections:
        sections.append(
            div(class_="text-lightest-hover text-center py-8")[
                i(data_lucide="check-circle", class_="inline-block w-8 h-8 mb-2"),
                p["No pending entries. All clear."],
            ]
        )

    return sections


def _entity_section(
    *,
    label: str,
    icon: str,
    entity_type: str,
    items: Sequence[PendingAuditEntity],
    creators: dict[int, User],
    local_date_formatter: Callable[[datetime | None], Element | str],
) -> Element:
    return div(class_="flex flex-col gap-2")[
        div(class_="flex items-baseline gap-2")[
            i(data_lucide=icon, class_="inline-block w-4 h-4"),
            h2[label],
            span(
                class_="text-xs font-semibold px-2 py-0.5 rounded bg-darker text-lightest-hover"
            )[str(len(items))],
        ],
        div(class_=TABLE_LIST_SCROLL)[
            table(class_="w-full text-sm")[
                thead[
                    tr(class_="text-left text-lightest-hover border-b border-darker")[
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
                            local_date_formatter=local_date_formatter,
                        )
                        for item in items
                    ]
                ],
            ],
        ],
    ]


def _entity_row(
    *,
    entity_type: str,
    entity: PendingAuditEntity,
    creators: dict[int, User],
    local_date_formatter: Callable[[datetime | None], Element | str],
) -> Element:
    from pindb.database.pin import Pin

    name: str = getattr(entity, "name", f"#{entity.id}")
    creator: User | None = (
        creators.get(entity.created_by_id) if entity.created_by_id else None
    )
    creator_name: str = creator.username if creator else "—"
    created_at: datetime | None = entity.created_at

    approve_url = f"/admin/pending/approve/{entity_type}/{entity.id}"
    reject_url = f"/admin/pending/reject/{entity_type}/{entity.id}"
    delete_url = f"/admin/pending/delete/{entity_type}/{entity.id}"

    dep_note: Element | str = ""
    if entity_type == "pin" and isinstance(entity, Pin):
        pending_deps = (
            [shop.name for shop in entity.shops if shop.is_pending]
            + [artist.name for artist in entity.artists if artist.is_pending]
            + [tag.display_name for tag in entity.tags if tag.is_pending]
        )
        if pending_deps:
            dep_note = span(class_="block text-xs text-error-main mt-0.5")[
                "Will also approve: " + ", ".join(pending_deps)
            ]

    return tr(class_="border-b border-darker hover:bg-main-hover")[
        td(class_="py-2 pr-6")[
            a(href=f"/get/{entity_type}/{entity.id}")[name], dep_note
        ],
        td(class_="py-2 pr-6 text-lighter-hover")[creator_name],
        td(class_="py-2 pr-6 text-lighter-hover")[local_date_formatter(created_at)],
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
                    )[i(data_lucide="x", class_="inline-block w-3 h-3 mr-1"), "Reject"]
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
