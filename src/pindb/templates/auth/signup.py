"""
htpy page and fragment builders: `templates/auth/signup.py`.
"""

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
    li,
    p,
    small,
    ul,
)

from pindb.password_policy import describe_policy
from pindb.templates.base import html_base
from pindb.templates.components.forms.error_message import error_message
from pindb.templates.components.layout.centered import centered_div


def signup_page(
    request: Request,
    error: str | None = None,
    password_errors: list[str] | None = None,
    *,
    google_enabled: bool = False,
    discord_enabled: bool = False,
    meta_enabled: bool = False,
) -> Element:
    policy = describe_policy()

    return html_base(
        title="Sign Up",
        request=request,
        body_content=centered_div(
            content=[
                h1["Sign Up"],
                hr,
                error_message(error),
                ul(class_="text-error-main list-disc pl-5")[
                    [li[rule] for rule in password_errors]
                ]
                if password_errors
                else None,
                form(
                    method="post",
                    action="/auth/signup",
                    class_="flex flex-col gap-2",
                )[
                    label(for_="username")["Username"],
                    input(
                        id="username",
                        name="username",
                        type="text",
                        required=True,
                        autocomplete="username",
                    ),
                    label(for_="email")["Email"],
                    input(
                        id="email",
                        name="email",
                        type="email",
                        required=True,
                        autocomplete="email",
                    ),
                    label(for_="password")["Password"],
                    input(
                        id="password",
                        name="password",
                        type="password",
                        required=True,
                        autocomplete="new-password",
                        minlength=str(policy.min_length),
                    ),
                    div(class_="text-sm text-subtle")[
                        p["Password requirements:"],
                        ul(class_="list-disc pl-5")[
                            [li[bullet] for bullet in policy.bullets()]
                        ],
                        small[
                            "We also check your password against a strength "
                            "estimator to reject easily guessed passphrases."
                        ],
                    ],
                    button(type="submit")["Create account"],
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
                div(class_="flex flex-col gap-2 mt-2")[
                    a(href="/auth/meta", class_="text-center")["Continue with Meta"]
                ]
                if meta_enabled
                else None,
                div(class_="mt-4")[
                    "Already have an account? ",
                    a(href="/auth/login")["Log in"],
                ],
            ],
            flex=True,
            col=True,
        ),
    )
