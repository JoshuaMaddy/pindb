from fastapi import Request
from htpy import (
    Element,
    a,
    button,
    div,
    form,
    h1,
    hr,
    input,
    label,
)

from pindb.config import CONFIGURATION
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div
from pindb.templates.components.error_message import error_message


def login_page(request: Request, error: str | None = None) -> Element:
    google_enabled = bool(
        CONFIGURATION.google_client_id and CONFIGURATION.google_client_secret
    )
    discord_enabled = bool(
        CONFIGURATION.discord_client_id and CONFIGURATION.discord_client_secret
    )

    return html_base(
        title="Login",
        request=request,
        body_content=centered_div(
            content=[
                h1["Login"],
                hr,
                error_message(error),
                form(
                    method="post",
                    action="/auth/login",
                    class_="flex flex-col gap-3",
                )[
                    label(for_="username")["Username"],
                    input(
                        id="username",
                        name="username",
                        type="text",
                        required=True,
                        autocomplete="username",
                    ),
                    label(for_="password")["Password"],
                    input(
                        id="password",
                        name="password",
                        type="password",
                        required=True,
                        autocomplete="current-password",
                    ),
                    button(type="submit")["Log in"],
                ],
                div(class_="flex flex-col gap-2 mt-4")[
                    a(href="/auth/google", class_="text-center")["Continue with Google"]
                ]
                if google_enabled
                else None,
                div(class_="flex flex-col gap-2 mt-2")[
                    a(href="/auth/discord", class_="text-center")[
                        "Continue with Discord"
                    ]
                ]
                if discord_enabled
                else None,
                div(class_="mt-4")[
                    "Don't have an account? ",
                    a(href="/auth/signup")["Sign up"],
                ],
            ],
            flex=True,
            col=True,
        ),
    )
