"""
htpy page and fragment builders: `templates/auth/security.py`.
"""

from __future__ import annotations

from fastapi import Request
from htpy import (
    Element,
    a,
    button,
    div,
    form,
    h1,
    h2,
    hr,
    input,
    label,
    li,
    p,
    ul,
)

from pindb.database.user import User
from pindb.password_policy import describe_policy
from pindb.templates.base import html_base
from pindb.templates.components.forms.error_message import error_message
from pindb.templates.components.layout.centered import centered_div


def security_page(
    request: Request,
    *,
    current_user: User,
    error: str | None = None,
    success: str | None = None,
    password_errors: list[str] | None = None,
) -> Element:
    policy = describe_policy()
    has_password = current_user.hashed_password is not None

    return html_base(
        title="Security",
        request=request,
        body_content=centered_div(
            content=[
                h1["Security settings"],
                hr,
                error_message(error),
                p(class_="text-green-200", role="status")[success] if success else None,
                ul(class_="text-error-main list-disc pl-5")[
                    [li[rule] for rule in password_errors]
                ]
                if password_errors
                else None,
                h2["Password"],
                p(class_="text-subtle")[
                    "Set a password" if not has_password else "Change your password"
                ],
                form(
                    method="post",
                    action="/user/me/password",
                    class_="flex flex-col gap-2",
                )[
                    (
                        [
                            label(for_="current_password")["Current password"],
                            input(
                                id="current_password",
                                name="current_password",
                                type="password",
                                required=True,
                                autocomplete="current-password",
                            ),
                        ]
                        if has_password
                        else None
                    ),
                    label(for_="new_password")["New password"],
                    input(
                        id="new_password",
                        name="new_password",
                        type="password",
                        required=True,
                        autocomplete="new-password",
                        minlength=str(policy.min_length),
                        aria_describedby="security-password-hint",
                    ),
                    label(for_="confirm_password")["Confirm new password"],
                    input(
                        id="confirm_password",
                        name="confirm_password",
                        type="password",
                        required=True,
                        autocomplete="new-password",
                        minlength=str(policy.min_length),
                        aria_describedby="security-password-hint",
                    ),
                    div(id="security-password-hint", class_="text-sm text-subtle")[
                        ul(class_="list-disc pl-5")[
                            [li[bullet] for bullet in policy.bullets()]
                        ],
                    ],
                    button(type="submit")[
                        "Set password" if not has_password else "Change password"
                    ],
                ],
                div(class_="mt-4")[
                    a(href=f"/user/{current_user.username}")["Back to profile"],
                ],
            ],
            flex=True,
            col=True,
        ),
    )
