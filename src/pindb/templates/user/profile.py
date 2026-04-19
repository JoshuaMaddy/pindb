from __future__ import annotations

from fastapi import Request
from htpy import Element, a, button, div, form, h3, hr, i, input, label, p, span

from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.user import User
from pindb.database.user_owned_pin import UserOwnedPin
from pindb.database.user_wanted_pin import UserWantedPin
from pindb.templates.base import html_base
from pindb.templates.components.card import card
from pindb.templates.components.centered import centered_div
from pindb.templates.components.confirm_modal import confirm_modal
from pindb.templates.components.delete_account_modal import delete_account_modal
from pindb.templates.components.empty_state import empty_state
from pindb.templates.components.icon_button import icon_button
from pindb.templates.components.page_heading import page_heading
from pindb.templates.components.pin_preview_card import pin_preview_card
from pindb.templates.components.thumbnail_grid import thumbnail_grid
from pindb.templates.user.pin_list_pages import unique_pins


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
    is_own_profile: bool = (
        current_user is not None and current_user.id == profile_user.id
    )

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
                is_own_profile and hr,
                is_own_profile
                and __settings_section(
                    request=request,
                    current_user=current_user,
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
            icon="layout-grid",
            text="Sets",
            extras=[
                is_own_profile
                and icon_button(
                    icon="layout-grid",
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
                        p[
                            pin_set.name,
                            span(class_="text-pin-base-300 ml-1")[
                                f"({len(pin_set.pins)})"
                            ],
                        ],
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
    pins: list[Pin] = unique_pins(entries=owned_pins)
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
    pins: list[Pin] = unique_pins(entries=wanted_pins)
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
    pins: list[Pin] = unique_pins(entries=tradeable_entries)
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


# (css_class, display_name, inspired_by, swatch_hex)
THEME_GROUPS: list[tuple[str, list[tuple[str, str, str]]]] = [
    (
        "Catppuccin",
        [
            ("mocha", "Mocha", "#89b4fa"),
            ("macchiato", "Macchiato", "#8aadf4"),
            ("frappe", "Frappé", "#8caaee"),
            ("latte", "Latte", "#1e66f5"),
        ],
    ),
    (
        "Dracula",
        [
            ("dracula", "Dracula", "#bd93f9"),
        ],
    ),
    (
        "Monokai",
        [
            ("monokai", "Monokai", "#a6e22e"),
            ("monokai-pro", "Monokai Pro", "#ff6188"),
        ],
    ),
    (
        "Nord",
        [
            ("nord", "Nord", "#88c0d0"),
            ("nord-light", "Nord Light", "#5e81ac"),
        ],
    ),
    (
        "Gruvbox",
        [
            ("gruvbox-dark-hard", "Dark Hard", "#cc241d"),
            ("gruvbox-dark", "Dark", "#d79921"),
            ("gruvbox-dark-soft", "Dark Soft", "#98971a"),
            ("gruvbox-light-soft", "Light Soft", "#79740e"),
            ("gruvbox-light", "Light", "#b57614"),
            ("gruvbox-light-hard", "Light Hard", "#d65d0e"),
        ],
    ),
]


VALID_THEME_VALUES: frozenset[str] = frozenset(
    value for _source, variants in THEME_GROUPS for value, _label, _swatch in variants
)


def __settings_section(
    request: Request,
    current_user: User | None,
) -> Element:
    assert current_user is not None
    current_theme: str = current_user.theme
    return div(class_="flex flex-col gap-4")[
        page_heading(icon="settings-2", text="Settings", level=2),
        div(class_="flex flex-col gap-4")[
            a(href="/user/me/security", class_="underline")[
                "Password & sign-in providers"
            ],
            form(
                hx_post=str(request.url_for("update_user_settings")),
                hx_trigger="change",
                hx_swap="none",
            )[
                [
                    div(class_="flex flex-col gap-2 mb-4")[
                        h3(
                            class_="text-xs font-semibold uppercase tracking-wider text-pin-base-300"
                        )[f"Inspired by {source}"],
                        div(class_="flex flex-wrap gap-2")[
                            [
                                label(
                                    class_=(
                                        "flex items-center gap-2 px-3 py-2 rounded-lg border"
                                        " cursor-pointer border-pin-border"
                                        " hover:border-pin-border-hover"
                                        " has-[:checked]:border-accent"
                                        " has-[:checked]:bg-pin-base-450"
                                    ),
                                )[
                                    input(
                                        type="radio",
                                        name="theme",
                                        value=value,
                                        checked=current_theme == value or None,
                                        class_="sr-only",
                                        onchange=f"document.documentElement.className = '{value} bg-pin-base-550'",
                                    ),
                                    span(
                                        class_="w-3 h-3 rounded-full shrink-0 border border-black/10",
                                        style=f"background-color:{swatch}",
                                    ),
                                    span(class_="text-sm")[label_text],
                                ]
                                for value, label_text, swatch in variants
                            ]
                        ],
                    ]
                    for source, variants in THEME_GROUPS
                ]
            ],
            div(class_=("mt-6 pt-6 border-t border-pin-base-400 flex flex-col gap-3"))[
                h3(
                    class_=(
                        "text-xs font-semibold uppercase tracking-wider "
                        "text-pin-base-300"
                    )
                )["Account"],
                delete_account_modal(
                    trigger=button(
                        type="button",
                        class_=(
                            "self-start text-sm text-red-300 underline "
                            "underline-offset-2 hover:text-red-200 cursor-pointer "
                            "bg-transparent border-0 p-0"
                        ),
                    )["Delete account"],
                    expected_username=current_user.username,
                    form_action=str(request.url_for("delete_own_account")),
                ),
            ],
        ],
    ]
