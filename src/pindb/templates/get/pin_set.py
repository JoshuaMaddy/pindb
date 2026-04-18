from typing import Sequence

from fastapi import Request
from htpy import Element, fragment

from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.user import User
from pindb.templates.base import html_base
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.centered import centered_div
from pindb.templates.components.confirm_modal import confirm_modal
from pindb.templates.components.description_block import description_block
from pindb.templates.components.icon_button import icon_button
from pindb.templates.components.page_heading import page_heading
from pindb.templates.components.paginated_pin_grid import paginated_pin_grid


def pin_set_page(
    request: Request,
    pin_set: PinSet,
    pins: Sequence[Pin],
    total_count: int,
    page: int,
    per_page: int,
) -> Element:
    user: User | None = getattr(getattr(request, "state", None), "user", None)
    can_edit: bool = user is not None and (pin_set.owner_id == user.id or user.is_admin)
    can_delete: bool = user is not None and (
        pin_set.owner_id == user.id or user.is_admin
    )

    return html_base(
        title=pin_set.name,
        request=request,
        body_content=centered_div(
            content=[
                bread_crumb(
                    entries=[
                        (request.url_for("get_list_index"), "List"),
                        (request.url_for("get_list_pin_sets"), "Pin Sets"),
                        ("(P) " + pin_set.name) if pin_set.is_pending else pin_set.name,
                    ]
                ),
                page_heading(
                    icon="layout-grid",
                    text=("(P) " + pin_set.name.title())
                    if pin_set.is_pending
                    else pin_set.name.title(),
                    extras=[
                        (user is not None and (user.is_admin or user.is_editor))
                        and icon_button(
                            icon="layers",
                            title="Bulk edit pins in this set",
                            href=f"/bulk-edit/from/pin_set/{pin_set.id}",
                        ),
                        (can_edit or can_delete)
                        and fragment[
                            can_edit
                            and icon_button(
                                icon="pencil",
                                title="Edit set",
                                href=str(
                                    request.url_for("get_edit_set", set_id=pin_set.id)
                                ),
                            ),
                            can_delete
                            and confirm_modal(
                                trigger=icon_button(
                                    icon="trash-2", title="Delete set", variant="danger"
                                ),
                                message=f'Delete the set "{pin_set.name}"? This won\'t delete any pins.',
                                form_action=str(
                                    request.url_for(
                                        "delete_personal_set", set_id=pin_set.id
                                    )
                                ),
                            ),
                        ],
                    ],
                    full_width=True,
                ),
                description_block(pin_set.description),
                paginated_pin_grid(
                    request=request,
                    pins=pins,
                    total_count=total_count,
                    page=page,
                    page_url=str(request.url_for("get_pin_set", id=pin_set.id)),
                    per_page=per_page,
                ),
            ],
            flex=True,
            col=True,
        ),
    )
