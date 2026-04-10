from __future__ import annotations

from fastapi import Request
from htpy import Element, a, div, hr, i, p

from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.user import User
from pindb.database.user_owned_pin import UserOwnedPin
from pindb.database.user_wanted_pin import UserWantedPin
from pindb.templates.base import html_base
from pindb.templates.components.card import card
from pindb.templates.components.centered import centered_div
from pindb.templates.components.confirm_modal import confirm_modal
from pindb.templates.components.empty_state import empty_state
from pindb.templates.components.icon_button import icon_button
from pindb.templates.components.page_heading import page_heading
from pindb.templates.components.pin_preview_card import pin_preview_card
from pindb.templates.components.thumbnail_grid import thumbnail_grid


def user_profile_page(
    request: Request,
    profile_user: User,
    favorite_pins: list[Pin],
    favorite_count: int,
    personal_sets: list[PinSet],
    owned_pins: list[UserOwnedPin],
    owned_count: int,
    wanted_pins: list[UserWantedPin],
    wanted_count: int,
    tradeable_entries: list[UserOwnedPin],
    tradeable_count: int,
    current_user: User | None,
) -> Element:
    username: str = profile_user.username

    return html_base(
        title=f"{username}'s Profile",
        request=request,
        body_content=centered_div(
            content=[
                page_heading(
                    icon="user",
                    text=username,
                ),
                hr,
                __favorites_section(
                    request=request,
                    pins=favorite_pins,
                    total=favorite_count,
                    username=username,
                ),
                hr,
                __sets_section(
                    request=request,
                    sets=personal_sets,
                    profile_user=profile_user,
                    current_user=current_user,
                ),
                hr,
                __collection_section(
                    request=request,
                    owned_pins=owned_pins,
                    total=owned_count,
                    username=username,
                ),
                hr,
                __want_list_section(
                    request=request,
                    wanted_pins=wanted_pins,
                    total=wanted_count,
                    username=username,
                ),
                hr,
                __tradeable_section(
                    request=request,
                    tradeable_entries=tradeable_entries,
                    total=tradeable_count,
                    username=username,
                ),
            ],
            flex=True,
            col=True,
        ),
    )


# ---------------------------------------------------------------------------
# Preview row helpers
# ---------------------------------------------------------------------------


def _see_all_card(url: str) -> Element:
    return a(
        href=url,
        class_=(
            "absolute right-0 top-0 bottom-0 z-20 w-12"
            " flex items-center justify-center"
            " rounded-lg bg-pin-base-450 border border-pin-base-400"
            " hover:border-accent hover:text-accent"
            " text-pin-base-300 no-underline"
        ),
    )[i(data_lucide="chevron-right")]


def _pin_preview_row(
    request: Request,
    pins: list[Pin],
    see_all_url: str,
) -> Element:
    return div(class_="relative")[
        div(
            class_=(
                "grid grid-flow-col grid-rows-[1fr_max-content]"
                " [grid-auto-columns:128px] gap-2 h-full pl-1 pr-16 [overflow-x:clip]"
            )
        )[[pin_preview_card(request=request, pin=pin) for pin in pins],],
        div(
            class_=(
                "absolute right-0 top-0 bottom-0 w-44 z-10 pointer-events-none"
                " bg-gradient-to-r from-transparent to-[var(--color-pin-base-550)]"
            )
        ),
        _see_all_card(url=see_all_url),
    ]


def _unique_pins_from_owned(owned_pins: list[UserOwnedPin]) -> list[Pin]:
    seen: set[int] = set()
    pins: list[Pin] = []
    for entry in owned_pins:
        if entry.pin_id not in seen:
            seen.add(entry.pin_id)
            pins.append(entry.pin)
    return pins


def _unique_pins_from_wanted(wanted_pins: list[UserWantedPin]) -> list[Pin]:
    seen: set[int] = set()
    pins: list[Pin] = []
    for entry in wanted_pins:
        if entry.pin_id not in seen:
            seen.add(entry.pin_id)
            pins.append(entry.pin)
    return pins


# ---------------------------------------------------------------------------
# Profile sections
# ---------------------------------------------------------------------------


def __favorites_section(
    request: Request,
    pins: list[Pin],
    total: int,
    username: str,
) -> Element:
    see_all_url: str = str(request.url_for("user_favorites_list", username=username))
    return div(class_="flex flex-col gap-2")[
        page_heading(
            icon="heart",
            text=f"Favorites ({total})",
            level=2,
        ),
        _pin_preview_row(request=request, pins=pins, see_all_url=see_all_url)
        if total > 0
        else empty_state("No favorited pins yet."),
    ]


def __sets_section(
    request: Request,
    sets: list[PinSet],
    profile_user: User,
    current_user: User | None,
) -> Element:
    is_own_profile: bool = (
        current_user is not None and current_user.id == profile_user.id
    )

    return div(class_="flex flex-col gap-2")[
        page_heading(
            icon="folder",
            text="Sets",
            extras=[
                is_own_profile
                and icon_button(
                    icon="folder-plus",
                    title="Create set",
                    href=str(request.url_for("get_create_user_set")),
                ),
            ],
            level=2,
        ),
        sets
        and [
            card(
                href=request.url_for("get_pin_set", id=pin_set.id),
                content=div(class_="flex gap-2 w-full")[
                    thumbnail_grid(request, pin_set.pins),
                    div[
                        p[pin_set.name],
                        p(class_="text-pin-base-300")[pin_set.description],
                    ],
                    is_own_profile
                    and div(
                        class_="flex gap-2 h-min grow justify-end",
                        onclick="event.stopPropagation()",
                    )[
                        icon_button(
                            icon="pencil",
                            title="Edit set",
                            href=str(
                                request.url_for("get_edit_set", set_id=pin_set.id)
                            ),
                        ),
                        confirm_modal(
                            trigger=icon_button(
                                icon="trash-2",
                                title="Delete set",
                                variant="danger",
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
            )
            for pin_set in sets
        ]
        or empty_state("No sets yet."),
    ]


def __collection_section(
    request: Request,
    owned_pins: list[UserOwnedPin],
    total: int,
    username: str,
) -> Element:
    see_all_url: str = str(request.url_for("user_collection_list", username=username))
    pins: list[Pin] = _unique_pins_from_owned(owned_pins=owned_pins)
    return div(class_="flex flex-col gap-2")[
        page_heading(
            icon="package-check",
            text=f"Collection ({total})",
            level=2,
        ),
        _pin_preview_row(request=request, pins=pins, see_all_url=see_all_url)
        if total > 0
        else empty_state("No pins in collection yet."),
    ]


def __want_list_section(
    request: Request,
    wanted_pins: list[UserWantedPin],
    total: int,
    username: str,
) -> Element:
    see_all_url: str = str(request.url_for("user_wants_list", username=username))
    pins: list[Pin] = _unique_pins_from_wanted(wanted_pins=wanted_pins)
    return div(class_="flex flex-col gap-2")[
        page_heading(
            icon="star",
            text=f"Want List ({total})",
            level=2,
        ),
        _pin_preview_row(request=request, pins=pins, see_all_url=see_all_url)
        if total > 0
        else empty_state("No pins on want list yet."),
    ]


def __tradeable_section(
    request: Request,
    tradeable_entries: list[UserOwnedPin],
    total: int,
    username: str,
) -> Element:
    see_all_url: str = str(request.url_for("user_trades_list", username=username))
    pins: list[Pin] = _unique_pins_from_owned(owned_pins=tradeable_entries)
    return div(class_="flex flex-col gap-2")[
        page_heading(
            icon="arrow-left-right",
            text=f"Trades ({total})",
            level=2,
        ),
        _pin_preview_row(request=request, pins=pins, see_all_url=see_all_url)
        if total > 0
        else empty_state("No pins marked as tradeable yet."),
    ]
