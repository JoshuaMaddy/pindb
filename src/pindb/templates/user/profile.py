from fastapi import Request
from htpy import Element, div, hr, p

from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.user import User
from pindb.templates.base import html_base
from pindb.templates.components.card import card
from pindb.templates.components.centered import centered_div
from pindb.templates.components.confirm_modal import confirm_modal
from pindb.templates.components.empty_state import empty_state
from pindb.templates.components.icon_button import icon_button
from pindb.templates.components.page_heading import page_heading
from pindb.templates.components.pin_grid import pin_grid
from pindb.templates.components.thumbnail_grid import thumbnail_grid


def user_profile_page(
    request: Request,
    profile_user: User,
    favorite_pins: list[Pin],
    personal_sets: list[PinSet],
    current_user: User | None,
) -> Element:
    return html_base(
        title=f"{profile_user.username}'s Profile",
        request=request,
        body_content=centered_div(
            content=[
                page_heading(
                    icon="user",
                    text=profile_user.username,
                    gap=3,
                ),
                hr,
                __favorites_section(request=request, pins=favorite_pins),
                hr,
                __sets_section(
                    request=request,
                    sets=personal_sets,
                    profile_user=profile_user,
                    current_user=current_user,
                ),
            ],
            flex=True,
            col=True,
        ),
    )


def __favorites_section(
    request: Request,
    pins: list[Pin],
) -> Element:
    return div(class_="flex flex-col gap-2")[
        page_heading(
            icon="heart",
            text="Favorites",
            level=2,
        ),
        pins
        and pin_grid(request=request, pins=pins)
        or empty_state("No favorited pins yet."),
    ]


def __sets_section(
    request: Request,
    sets: list[PinSet],
    profile_user: User,
    current_user: User | None,
) -> Element:
    is_own_profile = current_user is not None and current_user.id == profile_user.id

    return div(class_="flex flex-col gap-3")[
        page_heading(
            icon="folder",
            text="Sets",
            extras=[
                is_own_profile
                and icon_button(
                    icon="pen",
                    title="Edit pin",
                    href=str(request.url_for("get_my_sets")),
                ),
            ],
            level=2,
        ),
        sets
        and [
            card(
                href=request.url_for("get_pin_set", id=set.id),
                content=div(class_="flex gap-2 w-full")[
                    thumbnail_grid(request, set.pins),
                    div[
                        set.name,
                        p(class_="text-pin-base-300")[set.description],
                    ],
                    is_own_profile
                    and div(class_="flex gap-2 h-min grow justify-end")[
                        icon_button(
                            icon="pencil",
                            title="Edit set",
                            href=str(request.url_for("get_edit_set", set_id=set.id)),
                        ),
                        confirm_modal(
                            trigger=icon_button(
                                icon="trash-2",
                                title="Delete set",
                                variant="danger",
                            ),
                            message=f'Delete the set "{set.name}"? This won\'t delete any pins.',
                            form_action=str(
                                request.url_for("delete_personal_set", set_id=set.id)
                            ),
                        ),
                    ],
                ],
            )
            for set in sets
        ]
        or empty_state("No sets yet."),
    ]
