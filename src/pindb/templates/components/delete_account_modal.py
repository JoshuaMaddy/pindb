"""Confirmation modal for irreversible account deletion: user must type username."""

from __future__ import annotations

import json

from htpy import Element, button, div, form, i, input, label, p


def delete_account_modal(
    trigger: Element,
    expected_username: str,
    form_action: str,
) -> Element:
    """Alpine.js modal: *expected_username* must be entered before POST submit is enabled."""
    expected_json: str = json.dumps(expected_username)
    x_data: str = f"{{ open: false, expected: {expected_json}, typed: '' }}"

    confirm_btn_class = (
        "flex items-center gap-1 px-3 py-1.5 rounded border border-red-400 "
        "bg-transparent text-red-200 hover:bg-red-950/30 "
        "disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent"
    )
    cancel_class = (
        "flex items-center gap-1 px-3 py-1.5 rounded border border-pin-base-400 "
        "bg-transparent cursor-pointer text-pin-base-text hover:border-accent"
    )
    input_class = (
        "w-full px-3 py-2 rounded-lg border border-pin-base-400 bg-pin-base-550 "
        "text-pin-base-text placeholder:text-pin-base-400 focus:outline-none "
        "focus:border-accent"
    )

    modal_overlay: Element = div(
        class_="fixed inset-0 z-50 flex items-center justify-center bg-black/50",
        x_show="open",
        x_cloak=True,
        **{"@click.self": "open = false"},
    )[
        div(
            class_=(
                "relative bg-pin-base-500 border border-pin-base-400 rounded-xl "
                "shadow-2xl p-6 max-w-md w-full mx-4 flex flex-col gap-4"
            ),
            **{"@click.stop": ""},
        )[
            button(
                type="button",
                class_=(
                    "absolute top-3 right-3 flex items-center justify-center "
                    "w-6 h-6 rounded border-0 bg-transparent cursor-pointer "
                    "text-pin-base-300 hover:text-pin-base-text"
                ),
                **{"@click": "open = false"},
            )[i(data_lucide="x", class_="w-4 h-4")],
            p(class_="text-base font-medium text-pin-base-text")[
                "Delete your account permanently?"
            ],
            p(class_="text-sm text-pin-base-300")[
                "This removes your profile, sessions, linked sign-in providers, "
                "favorites, collection and want lists, and personal pin sets. "
                "Audit history that referred to you will be anonymised. "
                "This cannot be undone."
            ],
            form(
                method="post",
                action=form_action,
                class_="flex flex-col gap-4",
            )[
                div(class_="flex flex-col gap-2")[
                    label(class_="text-sm text-pin-base-300")[
                        "Type your username to confirm:"
                    ],
                    input(
                        type="text",
                        name="confirm_username",
                        autocomplete="off",
                        class_=input_class,
                        placeholder=expected_username,
                        **{
                            "x-model": "typed",
                            "@keydown.escape": "open = false",
                        },
                    ),
                ],
                div(class_="flex gap-2 justify-end")[
                    button(
                        type="button",
                        class_=cancel_class,
                        **{"@click": "open = false"},
                    )["Cancel"],
                    button(
                        type="submit",
                        class_=confirm_btn_class,
                        **{":disabled": "typed !== expected"},
                    )["Delete my account"],
                ],
            ],
        ]
    ]

    return div(
        class_="inline-flex items-center self-start",
        x_data=x_data,
    )[
        div(
            class_="inline-flex items-center",
            **{"@click": "open = true; typed = ''"},
        )[trigger],
        modal_overlay,
    ]
