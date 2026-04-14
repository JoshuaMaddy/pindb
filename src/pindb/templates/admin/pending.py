from datetime import datetime
from typing import Sequence

from fastapi import Request
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

from pindb.database.artist import Artist
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

_TABLE_TO_SLUG: dict[str, str] = {
    "pins": "pin",
    "shops": "shop",
    "artists": "artist",
    "tags": "tag",
    "pin_sets": "pin_set",
}


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
) -> Element:
    edit_groups = edit_groups or {}
    edit_group_entities = edit_group_entities or {}
    total = (
        len(pending_pins)
        + len(pending_shops)
        + len(pending_artists)
        + len(pending_tags)
        + len(pending_pin_sets)
        + len(edit_groups)
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
        table(class_="w-full text-sm")[
            thead[
                tr(class_="text-left text-pin-base-300 border-b border-pin-base-700")[
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
    creator_name: str = creator.username if creator else "—"
    created_at: datetime | None = entity.created_at
    created_str: str = created_at.strftime("%Y-%m-%d %H:%M") if created_at else "—"

    approve_url = f"/admin/pending/approve/{entity_type}/{entity.id}"
    reject_url = f"/admin/pending/reject/{entity_type}/{entity.id}"
    delete_url = f"/admin/pending/delete/{entity_type}/{entity.id}"

    # Show pending dependencies for pins
    dep_note: Element | str = ""
    if entity_type == "pin" and isinstance(entity, Pin):
        pending_deps = (
            [shop.name for shop in entity.shops if shop.is_pending]
            + [artist.name for artist in entity.artists if artist.is_pending]
            + [tag.name for tag in entity.tags if tag.is_pending]
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
        table(class_="w-full text-sm")[
            thead[
                tr(class_="text-left text-pin-base-300 border-b border-pin-base-700")[
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
                        key=lambda kv: (kv[0][0], kv[0][1]),
                    )
                ]
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
    slug: str = _TABLE_TO_SLUG.get(table_name, table_name)
    name: str = getattr(entity, "name", f"#{entity_id}") if entity else f"#{entity_id}"
    latest = chain[-1] if chain else None
    latest_editor: str = "—"
    latest_at: str = "—"
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
