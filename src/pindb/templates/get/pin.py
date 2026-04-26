"""
htpy page and fragment builders: `templates/get/pin.py`.

Top-level pin detail page composition. Image carousel, lightbox, details
column, and HTMX fragments live in sibling modules.
"""

from fastapi import Request
from htpy import Element, div, fragment
from markupsafe import Markup

from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.user import User
from pindb.database.user_owned_pin import UserOwnedPin
from pindb.database.user_wanted_pin import UserWantedPin
from pindb.templates.base import html_base
from pindb.templates.components.audit_timestamps import audit_timestamps
from pindb.templates.components.back_link import back_link
from pindb.templates.components.confirm_modal import confirm_modal
from pindb.templates.components.icon_button import icon_button
from pindb.templates.components.page_heading import page_heading
from pindb.templates.components.pending_edit_banner import pending_edit_banner
from pindb.templates.components.pin_image_carousel import (
    PIN_SWIPER_INIT,
    pin_image_carousel,
)
from pindb.templates.components.pin_lightbox import PIN_LIGHTBOX_INIT, pin_lightbox
from pindb.templates.get.pin_details import pin_details

# Re-exported for backwards compatibility — route handlers import from here.
from pindb.templates.get.pin_fragments import favorite_button, set_row

__all__ = ["pin_page", "favorite_button", "set_row"]


def pin_page(
    request: Request,
    pin: Pin,
    is_favorited: bool = False,
    user_sets: list[PinSet] | None = None,
    owned_entries: list[UserOwnedPin] | None = None,
    wanted_entries: list[UserWantedPin] | None = None,
    has_pending_chain: bool = False,
    viewing_pending: bool = False,
) -> Element:
    user: User | None = getattr(getattr(request, "state", None), "user", None)
    canonical_url = str(request.url_for("get_pin", id=pin.id))
    pending_url = canonical_url + "?version=pending"
    return html_base(
        title=pin.name,
        request=request,
        script_content=Markup(PIN_SWIPER_INIT + PIN_LIGHTBOX_INIT),
        body_content=fragment[
            _page_layout(
                request=request,
                pin=pin,
                user=user,
                is_favorited=is_favorited,
                user_sets=user_sets or [],
                owned_entries=owned_entries or [],
                wanted_entries=wanted_entries or [],
                has_pending_chain=has_pending_chain,
                viewing_pending=viewing_pending,
                canonical_url=canonical_url,
                pending_url=pending_url,
            ),
            pin_lightbox(),
        ],
    )


def _page_layout(
    request: Request,
    pin: Pin,
    user: User | None,
    is_favorited: bool,
    user_sets: list[PinSet],
    owned_entries: list[UserOwnedPin],
    wanted_entries: list[UserWantedPin],
    has_pending_chain: bool,
    viewing_pending: bool,
    canonical_url: str,
    pending_url: str,
) -> Element:
    return div(
        class_="mx-auto px-10 my-5 gap-2 w-full grid grid-cols-1 md:gap-8 md:grid-cols-2 md:max-w-[160ch]"
    )[
        div(class_="md:col-span-2")[
            back_link(),
            has_pending_chain
            and pending_edit_banner(
                viewing_pending=viewing_pending,
                canonical_url=canonical_url,
                pending_url=pending_url,
            ),
            page_heading(
                icon="circle-star",
                text=("(P) " + pin.name) if pin.is_pending else pin.name,
                full_width=True,
                extras=fragment[
                    user
                    and (user.is_admin or user.is_editor)
                    and icon_button(
                        icon="pen",
                        title="Edit pin",
                        href=str(request.url_for("get_edit_pin", id=pin.id)),
                    ),
                    user
                    and (user.is_admin or user.is_editor)
                    and icon_button(
                        icon="copy",
                        title="Duplicate pin (prefills a new pin form, minus images)",
                        href=str(
                            request.url_for("get_create_pin").include_query_params(
                                duplicate_from=pin.id
                            )
                        ),
                    ),
                    user
                    and user.is_admin
                    and confirm_modal(
                        trigger=icon_button(
                            icon="trash-2",
                            title="Delete pin",
                            variant="danger",
                        ),
                        message=f'Delete the pin "{pin.name}"? This will delete the pin!',
                        form_action=str(
                            request.url_for(
                                "post_delete_entity",
                                entity_type="pin",
                                id=pin.id,
                            )
                        ),
                    ),
                ],
            ),
            audit_timestamps(
                created_at=pin.created_at,
                updated_at=pin.updated_at,
            ),
        ],
        div(class_="w-full overflow-x-visible")[
            pin_image_carousel(request=request, pin=pin),
        ],
        pin_details(
            request=request,
            pin=pin,
            user=user,
            is_favorited=is_favorited,
            user_sets=user_sets,
            owned_entries=owned_entries,
            wanted_entries=wanted_entries,
        ),
    ]
