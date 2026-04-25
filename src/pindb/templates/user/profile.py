"""
htpy page and fragment builders: `templates/user/profile.py`.
"""

from __future__ import annotations

from typing import Literal

from fastapi import Request
from htpy import Element, a, button, div, form, h3, hr, i, input, label, p, script, span
from markupsafe import Markup
from pydantic import BaseModel, ConfigDict

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


def _see_all_card(url: str, label: str) -> Element:
    return a(
        href=url,
        aria_label=label,
        class_=(
            "absolute right-0 top-0 bottom-0 z-20 w-12"
            " flex items-center justify-center"
            " rounded-lg bg-pin-base-450 border border-pin-base-400"
            " hover:border-accent hover:text-accent"
            " text-pin-base-300 no-underline"
        ),
    )[i(data_lucide="chevron-right", aria_hidden="true")]


def _pin_preview_row(
    request: Request,
    pins: list[Pin],
    see_all_url: str,
    see_all_label: str,
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
        _see_all_card(url=see_all_url, label=see_all_label),
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
        _pin_preview_row(
            request=request,
            pins=pins,
            see_all_url=see_all_url,
            see_all_label=f"See all favorites for {username}",
        )
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
        _pin_preview_row(
            request=request,
            pins=pins,
            see_all_url=see_all_url,
            see_all_label=f"See all collection pins for {username}",
        )
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
        _pin_preview_row(
            request=request,
            pins=pins,
            see_all_url=see_all_url,
            see_all_label=f"See all wanted pins for {username}",
        )
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
        _pin_preview_row(
            request=request,
            pins=pins,
            see_all_url=see_all_url,
            see_all_label=f"See all tradeable pins for {username}",
        )
        if total > 0
        else empty_state("No pins marked as tradeable yet."),
    ]


ThemeAppearance = Literal["dark", "light"]


class ThemeVariant(BaseModel):
    """One selectable UI theme (stored as ``User.theme`` = ``value``)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: str
    label: str
    appearance: ThemeAppearance
    swatch_hex: str


class ThemeSection(BaseModel):
    """A themed heading plus its radio variants on the profile settings form."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    section_heading: str
    variants: tuple[ThemeVariant, ...]


THEME_GROUPS: tuple[ThemeSection, ...] = (
    ThemeSection(
        section_heading="Accessibility",
        variants=(
            ThemeVariant(
                value="hc-dark",
                label="High Contrast Dark",
                appearance="dark",
                swatch_hex="#ffff00",
            ),
            ThemeVariant(
                value="hc-light",
                label="High Contrast Light",
                appearance="light",
                swatch_hex="#0044b3",
            ),
        ),
    ),
    ThemeSection(
        section_heading="Inspired by Catppuccin",
        variants=(
            ThemeVariant(
                value="mocha", label="Mocha", appearance="dark", swatch_hex="#89b4fa"
            ),
            ThemeVariant(
                value="macchiato",
                label="Macchiato",
                appearance="dark",
                swatch_hex="#8aadf4",
            ),
            ThemeVariant(
                value="frappe", label="Frappé", appearance="dark", swatch_hex="#8caaee"
            ),
            ThemeVariant(
                value="latte", label="Latte", appearance="light", swatch_hex="#1e66f5"
            ),
        ),
    ),
    ThemeSection(
        section_heading="Inspired by Dracula",
        variants=(
            ThemeVariant(
                value="dracula",
                label="Dracula",
                appearance="dark",
                swatch_hex="#bd93f9",
            ),
        ),
    ),
    ThemeSection(
        section_heading="Inspired by Monokai",
        variants=(
            ThemeVariant(
                value="monokai",
                label="Monokai",
                appearance="dark",
                swatch_hex="#a6e22e",
            ),
            ThemeVariant(
                value="monokai-pro",
                label="Monokai Pro",
                appearance="dark",
                swatch_hex="#ff6188",
            ),
        ),
    ),
    ThemeSection(
        section_heading="Inspired by Nord",
        variants=(
            ThemeVariant(
                value="nord", label="Nord", appearance="dark", swatch_hex="#88c0d0"
            ),
            ThemeVariant(
                value="nord-light",
                label="Nord Light",
                appearance="light",
                swatch_hex="#5e81ac",
            ),
        ),
    ),
    ThemeSection(
        section_heading="Inspired by Gruvbox",
        variants=(
            ThemeVariant(
                value="gruvbox-dark-hard",
                label="Dark Hard",
                appearance="dark",
                swatch_hex="#cc241d",
            ),
            ThemeVariant(
                value="gruvbox-dark",
                label="Dark",
                appearance="dark",
                swatch_hex="#d79921",
            ),
            ThemeVariant(
                value="gruvbox-dark-soft",
                label="Dark Soft",
                appearance="dark",
                swatch_hex="#98971a",
            ),
            ThemeVariant(
                value="gruvbox-light-soft",
                label="Light Soft",
                appearance="light",
                swatch_hex="#79740e",
            ),
            ThemeVariant(
                value="gruvbox-light",
                label="Light",
                appearance="light",
                swatch_hex="#b57614",
            ),
            ThemeVariant(
                value="gruvbox-light-hard",
                label="Light Hard",
                appearance="light",
                swatch_hex="#d65d0e",
            ),
        ),
    ),
)


VALID_THEME_VALUES: frozenset[str] = frozenset(
    v.value for section in THEME_GROUPS for v in section.variants
)

VALID_DIMENSION_UNITS: frozenset[str] = frozenset({"mm", "in"})

# Browsers may restore theme radio state on hard reload and fire `change`; an inline
# `onchange` then overwrote `<html class>` with the wrong theme. Sync from the server
# class on `load`, then listen for real user changes only (listener attached after sync).
_USER_SETTINGS_FORM_SCRIPT: str = """
(function () {
  function syncThemeRadiosFromHtmlClass() {
    var root = document.documentElement;
    var cls = root.className || "";
    var theme = (cls.match(/^([^\\s]+)/) || [, "mocha"])[1];
    var form = document.getElementById("user-settings-form");
    if (!form) return;
    form.querySelectorAll('input[name="theme"]').forEach(function (inp) {
      inp.checked = inp.value === theme;
    });
  }
  function syncDimensionRadiosFromDataAttr() {
    var form = document.getElementById("user-settings-form");
    if (!form) return;
    var du = form.getAttribute("data-dimension-unit");
    if (!du) return;
    form.querySelectorAll('input[name="dimension_unit"]').forEach(function (inp) {
      inp.checked = inp.value === du;
    });
  }
  function onThemeRadioChange(ev) {
    var t = ev.target;
    if (!t || t.name !== "theme" || t.type !== "radio" || !t.checked) return;
    document.documentElement.className = t.value + " bg-pin-base-550";
  }
  function boot() {
    if (!document.getElementById("user-settings-form")) return;
    syncThemeRadiosFromHtmlClass();
    syncDimensionRadiosFromDataAttr();
    setTimeout(function () {
      document.body.addEventListener("change", onThemeRadioChange);
    }, 0);
  }
  if (document.readyState === "complete") {
    boot();
  } else {
    window.addEventListener("load", boot);
  }
})();
"""


def __settings_section(
    request: Request,
    current_user: User | None,
) -> Element:
    assert current_user is not None
    current_theme: str = current_user.theme
    raw_dimension_unit: str = current_user.dimension_unit
    current_dimension_unit: str = (
        raw_dimension_unit if raw_dimension_unit in VALID_DIMENSION_UNITS else "mm"
    )
    return div(class_="flex flex-col gap-4")[
        page_heading(icon="settings-2", text="Settings", level=2),
        div(class_="flex flex-col gap-4")[
            a(href="/user/me/security", class_="underline")[
                "Password & sign-in providers"
            ],
            form(
                id="user-settings-form",
                autocomplete="off",
                **{"data-dimension-unit": current_dimension_unit},
                hx_post=str(request.url_for("update_user_settings")),
                hx_trigger="change",
                hx_swap="none",
            )[
                [
                    div(class_="flex flex-col gap-2 mb-4")[
                        h3(
                            class_="text-xs font-semibold uppercase tracking-wider text-pin-base-300"
                        )[section.section_heading],
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
                                        value=variant.value,
                                        checked=current_theme == variant.value or None,
                                        class_="sr-only",
                                    ),
                                    span(
                                        class_="inline-flex shrink-0 items-center",
                                        style=f"color:{variant.swatch_hex}",
                                    )[
                                        i(
                                            data_lucide=(
                                                "sun"
                                                if variant.appearance == "light"
                                                else "moon"
                                            ),
                                            class_=(
                                                "theme-appearance-icon inline-block h-4 w-4 "
                                                "shrink-0 text-inherit "
                                                + (
                                                    "theme-appearance-sun"
                                                    if variant.appearance == "light"
                                                    else "theme-appearance-moon"
                                                )
                                            ),
                                            aria_hidden="true",
                                        ),
                                    ],
                                    span(class_="text-sm")[variant.label],
                                ]
                                for variant in section.variants
                            ]
                        ],
                    ]
                    for section in THEME_GROUPS
                ],
                div(class_="flex flex-col gap-2 mt-6")[
                    h3(
                        class_=(
                            "text-xs font-semibold uppercase tracking-wider "
                            "text-pin-base-300"
                        )
                    )["Pin dimensions"],
                    p(class_="text-sm text-pin-base-300 mb-1")[
                        "How sizes appear on pin detail pages."
                    ],
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
                                    name="dimension_unit",
                                    value=value,
                                    checked=current_dimension_unit == value or None,
                                    class_="sr-only",
                                ),
                                span(class_="text-sm")[label_text],
                            ]
                            for value, label_text in (
                                ("mm", "Millimeters (mm)"),
                                ("in", "Inches (in)"),
                            )
                        ],
                    ],
                ],
            ],
            script[Markup(_USER_SETTINGS_FORM_SCRIPT)],
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
                            "self-start text-sm text-red-600 underline "
                            "underline-offset-2 hover:text-red-500 cursor-pointer "
                            "bg-transparent border-0 p-0"
                        ),
                    )["Delete account"],
                    expected_username=current_user.username,
                    form_action=str(request.url_for("delete_own_account")),
                ),
            ],
        ],
    ]
