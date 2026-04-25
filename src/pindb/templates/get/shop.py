"""
htpy page and fragment builders: `templates/get/shop.py`.
"""

from typing import Sequence

from fastapi import Request
from htpy import Element, a, br, code, div, fragment, h2

from pindb.database import Shop, User
from pindb.database.pin import Pin
from pindb.templates.base import html_base
from pindb.templates.components.audit_timestamps import audit_timestamps
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.centered import centered_div
from pindb.templates.components.confirm_modal import confirm_modal
from pindb.templates.components.description_block import description_block
from pindb.templates.components.icon_button import icon_button
from pindb.templates.components.linked_items_row import linked_items_row
from pindb.templates.components.page_heading import page_heading
from pindb.templates.components.paginated_pin_grid import paginated_pin_grid
from pindb.templates.components.pending_edit_banner import pending_edit_banner


def shop_page(
    request: Request,
    shop: Shop,
    pins: Sequence[Pin],
    total_count: int,
    page: int,
    per_page: int,
    has_pending_chain: bool = False,
    viewing_pending: bool = False,
) -> Element:
    user: User | None = getattr(getattr(request, "state", None), "user", None)
    canonical_url = str(request.url_for("get_shop", id=shop.id))
    pending_url = canonical_url + "?version=pending"
    return html_base(
        title=shop.name,
        request=request,
        body_content=centered_div(
            content=fragment[
                bread_crumb(
                    entries=[
                        (request.url_for("get_list_index"), "List"),
                        (request.url_for("get_list_shops"), "Shops"),
                        ("(P) " + shop.name) if shop.is_pending else shop.name,
                    ]
                ),
                has_pending_chain
                and pending_edit_banner(
                    viewing_pending=viewing_pending,
                    canonical_url=canonical_url,
                    pending_url=pending_url,
                ),
                page_heading(
                    icon="store",
                    text=("(P) " + shop.name) if shop.is_pending else shop.name,
                    full_width=True,
                    extras=fragment[
                        user
                        and (user.is_admin or user.is_editor)
                        and icon_button(
                            icon="layers",
                            title="Bulk edit this shop's pins",
                            href=f"/bulk-edit/from/shop/{shop.id}",
                        ),
                        user
                        and (user.is_admin or user.is_editor)
                        and icon_button(
                            icon="pen",
                            title="Edit shop",
                            href=str(request.url_for("get_edit_shop", id=shop.id)),
                        ),
                        user
                        and user.is_admin
                        and confirm_modal(
                            trigger=icon_button(
                                icon="trash-2",
                                title="Delete shop",
                                variant="danger",
                            ),
                            message=f'Delete the shop "{shop.name}"?',
                            form_action=str(
                                request.url_for(
                                    "post_delete_entity",
                                    entity_type="shop",
                                    id=shop.id,
                                )
                            ),
                        ),
                    ],
                ),
                description_block(shop.description),
                audit_timestamps(
                    created_at=shop.created_at,
                    updated_at=shop.updated_at,
                ),
                bool(shop.aliases)
                and linked_items_row(
                    icon="arrow-left-right",
                    label="Also known as",
                    items=[
                        code(
                            class_="bg-pin-base-700 text-pin-base-text rounded px-1.5 py-0.5 text-sm font-mono"
                        )[a.alias]
                        for a in sorted(shop.aliases, key=lambda a: a.alias)
                    ],
                ),
                fragment[
                    bool(len(shop.links))
                    and div[
                        h2["Links"],
                        *[
                            fragment[a(href=link.path)[link.path], br]
                            for link in shop.links
                        ],
                    ]
                ],
                paginated_pin_grid(
                    request=request,
                    pins=pins,
                    total_count=total_count,
                    page=page,
                    page_url=str(request.url_for("get_shop", id=shop.id)),
                    per_page=per_page,
                ),
            ],
            flex=True,
            col=True,
        ),
    )
