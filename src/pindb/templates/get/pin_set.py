"""
htpy page and fragment builders: `templates/get/pin_set.py`.
"""

from typing import Sequence

from fastapi import Request
from htpy import Element, fragment

from pindb.database.entity_type import EntityType
from pindb.database.pending_edit_utils import PendingChange
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.user import User
from pindb.routes._urls import pin_set_url
from pindb.templates.base import html_base
from pindb.templates.components.dialogs.confirm_modal import confirm_modal
from pindb.templates.components.display.changes_requested_banner import (
    changes_requested_banner,
)
from pindb.templates.components.display.description_block import description_block
from pindb.templates.components.display.pending_changes_table import (
    pending_changes_table,
)
from pindb.templates.components.display.pending_edit_banner import pending_edit_banner
from pindb.templates.components.display.review_actions import review_actions_bar
from pindb.templates.components.forms.icon_button import icon_button
from pindb.templates.components.layout.centered import centered_div
from pindb.templates.components.layout.page_heading import page_heading
from pindb.templates.components.nav.bread_crumb import bread_crumb
from pindb.templates.components.pins.paginated_pin_grid import paginated_pin_grid
from pindb.utils import pretty_titlecase, review_label


def pin_set_page(
    request: Request,
    pin_set: PinSet,
    pins: Sequence[Pin],
    total_count: int,
    page: int,
    per_page: int,
    has_pending_chain: bool = False,
    viewing_pending: bool = False,
    pending_changes: Sequence[PendingChange] = (),
    edit_change_request: str | None = None,
) -> Element:
    user: User | None = getattr(getattr(request, "state", None), "user", None)
    is_global: bool = pin_set.owner_id is None
    can_edit: bool = user is not None and (
        pin_set.owner_id == user.id or user.is_admin or (is_global and user.is_editor)
    )
    can_delete: bool = user is not None and (
        pin_set.owner_id == user.id or user.is_admin
    )
    # An admin looking at an unapproved set rules on it from the review bar, which
    # carries its own Delete; a second Delete in the heading would only be ambiguous.
    in_review: bool = (
        user is not None
        and user.is_admin
        and (pin_set.is_pending or pin_set.is_rejected)
    )
    canonical_url = str(pin_set_url(request=request, pin_set=pin_set))
    pending_url = canonical_url + "?version=pending"
    share_description: str = pin_set.description or f"View {pin_set.name} on PinDB."

    return html_base(
        title=pin_set.name,
        request=request,
        body_content=centered_div(
            content=[
                bread_crumb(
                    entries=[
                        (request.url_for("get_list_index"), "List"),
                        (request.url_for("get_list_pin_sets"), "Pin Sets"),
                        review_label(
                            pin_set.name,
                            is_pending=pin_set.is_pending,
                            is_rejected=pin_set.is_rejected,
                        ),
                    ]
                ),
                pin_set.is_rejected
                and changes_requested_banner(
                    reason=pin_set.rejection_reason,
                    edit_url=str(request.url_for("get_edit_set", set_id=pin_set.id))
                    if can_edit
                    else None,
                ),
                edit_change_request
                and changes_requested_banner(
                    reason=edit_change_request,
                    edit_url=str(request.url_for("get_edit_set", set_id=pin_set.id)),
                    is_edit=True,
                ),
                has_pending_chain
                and not edit_change_request
                and pending_edit_banner(
                    viewing_pending=viewing_pending,
                    canonical_url=canonical_url,
                    pending_url=pending_url,
                ),
                viewing_pending and pending_changes_table(pending_changes),
                in_review
                and review_actions_bar(
                    entity_type=EntityType.pin_set,
                    entity_id=pin_set.id,
                    entity_name=pin_set.name,
                    is_rejected=pin_set.is_rejected,
                ),
                page_heading(
                    icon="layout-grid",
                    text=review_label(
                        pretty_titlecase(pin_set.name),
                        is_pending=pin_set.is_pending,
                        is_rejected=pin_set.is_rejected,
                    ),
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
                            and not in_review
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
                                htmx_post=True,
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
                    page_url=canonical_url,
                    per_page=per_page,
                ),
            ],
            flex=True,
            col=True,
        ),
    )
