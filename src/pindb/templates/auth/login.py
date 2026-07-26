"""
htpy page and fragment builders: `templates/auth/login.py`.
"""

from fastapi import Request
from htpy import (
    Element,
    button,
    form,
    h1,
    hr,
    input,
    label,
    p,
)

from pindb.templates.base import html_base
from pindb.templates.components.forms.error_message import error_message
from pindb.templates.components.layout.centered import centered_div


def login_page(
    request: Request,
    error: str | None = None,
    *,
    next_target: str | None = None,
) -> Element:
    """Render the login page — the only page an anonymous visitor can reach.

    Args:
        request (Request): Incoming request.
        error (str | None): Message to show above the form.
        next_target (str | None): Validated site-relative path to return to
            after login, carried through as a hidden field.
    """
    return html_base(
        title="Login",
        request=request,
        body_content=centered_div(
            content_width="small",
            content=[
                h1["Login"],
                p(class_="text-sm text-base-text")["Private, invite-only community."],
                hr,
                error_message(error),
                form(
                    method="post",
                    action="/auth/login",
                    class_="flex flex-col gap-2",
                )[
                    input(type="hidden", name="next", value=next_target)
                    if next_target
                    else None,
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
            ],
            flex=True,
            col=True,
        ),
    )
