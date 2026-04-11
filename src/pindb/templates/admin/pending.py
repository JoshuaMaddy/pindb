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
from pindb.database.material import Material
from pindb.database.pending_mixin import PendingAuditEntity
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.shop import Shop
from pindb.database.tag import Tag
from pindb.database.user import User
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div
from pindb.templates.components.page_heading import page_heading


def pending_page(
    request: Request,
    pending_pins: list[Pin],
    pending_shops: list[Shop],
    pending_artists: list[Artist],
    pending_tags: list[Tag],
    pending_materials: list[Material],
    pending_pin_sets: list[PinSet],
    creators: dict[int, User],
) -> Element:
    total = (
        len(pending_pins)
        + len(pending_shops)
        + len(pending_artists)
        + len(pending_tags)
        + len(pending_materials)
        + len(pending_pin_sets)
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
                    "Approving a pin also approves its pending dependencies (shops, artists, materials, tags)."
                ],
                hr,
                *_sections(
                    request,
                    pending_pins,
                    pending_shops,
                    pending_artists,
                    pending_tags,
                    pending_materials,
                    pending_pin_sets,
                    creators,
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
    pending_materials: list[Material],
    pending_pin_sets: list[PinSet],
    creators: dict[int, User],
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
        label="Materials",
        icon="layers",
        entity_type="material",
        items=pending_materials,
    )
    _add(
        label="Pin Sets",
        icon="library",
        entity_type="pin_set",
        items=pending_pin_sets,
    )

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
            + [material.name for material in entity.materials if material.is_pending]
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
                        type_="submit",
                        class_="btn btn-sm btn-primary",
                        title="Approve",
                    )[
                        i(data_lucide="check", class_="inline-block w-3 h-3 mr-1"),
                        "Approve",
                    ]
                ],
                form(method="post", action=reject_url)[
                    button(
                        type_="submit",
                        class_="btn btn-sm btn-warning",
                        title="Reject",
                    )[
                        i(data_lucide="x", class_="inline-block w-3 h-3 mr-1"),
                        "Reject",
                    ]
                ],
                form(method="post", action=delete_url)[
                    button(
                        type_="submit",
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
