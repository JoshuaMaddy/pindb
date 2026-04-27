"""
Profile settings section and related theme definitions.
"""

from typing import Literal

from fastapi import Request
from htpy import Element, a, button, div, form, h3, i, input, label, p, script, span
from markupsafe import Markup
from pydantic import BaseModel, ConfigDict

from pindb.database.user import User
from pindb.templates.components.delete_account_modal import delete_account_modal
from pindb.templates.components.page_heading import page_heading

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


VALID_DIMENSION_UNITS: frozenset[str] = frozenset({"mm", "in"})
VALID_THEME_VALUES: frozenset[str] = frozenset(
    variant.value for section in THEME_GROUPS for variant in section.variants
)

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


def settings_section(
    *,
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
                                        " cursor-pointer border-lightest"
                                        " hover:border-lightest-hover"
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
                                    " cursor-pointer border-lightest"
                                    " hover:border-lightest-hover"
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
            div(class_="mt-6 pt-6 border-t border-pin-base-400 flex flex-col gap-3")[
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
