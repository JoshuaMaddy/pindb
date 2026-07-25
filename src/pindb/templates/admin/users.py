"""
htpy page and fragment builders: `templates/admin/users.py`.
"""

from typing import Sequence

from fastapi import Request
from htpy import (
    Element,
    button,
    details,
    div,
    form,
    h1,
    hr,
    i,
    input,
    label,
    li,
    p,
    summary,
    ul,
)

from pindb.database.user import User
from pindb.password_policy import describe_policy
from pindb.templates.base import html_base
from pindb.templates.components.forms.error_message import error_message
from pindb.templates.components.islands import island
from pindb.templates.components.layout.centered import centered_div


def _create_user_form() -> Element:
    """Account-creation form — the only path to a new account.

    Deliberately a plain server-rendered form rather than an island: it sits
    beside the existing admin-users island but shares nothing with it, and a
    form needs no client state.
    """
    policy = describe_policy()
    return details(class_="w-full")[
        summary(class_="cursor-pointer")["Create a user"],
        div(class_="mt-3")[
            p(class_="text-subtle text-sm")[
                "There is no self-service signup. New members get an account "
                "here, and there is no password reset — a member who is locked "
                "out needs a new password set from this page."
            ],
            _create_user_form_body(
                policy_bullets=list(policy.bullets()),
                min_length=policy.min_length,
            ),
        ],
    ]


def _create_user_form_body(*, policy_bullets: list[str], min_length: int) -> Element:
    return form(
        method="post",
        action="/admin/users/create",
        class_="flex flex-col gap-2",
    )[
        label(for_="new_username")["Username"],
        input(
            id="new_username",
            name="username",
            type="text",
            required=True,
            autocomplete="off",
        ),
        label(for_="new_email")["Email"],
        input(
            id="new_email",
            name="email",
            type="email",
            required=True,
            autocomplete="off",
        ),
        label(for_="new_password")["Password"],
        input(
            id="new_password",
            name="password",
            type="password",
            required=True,
            autocomplete="new-password",
            minlength=str(min_length),
            aria_describedby="new-user-password-hint",
        ),
        div(id="new-user-password-hint", class_="text-sm text-subtle")[
            ul(class_="list-disc pl-5")[[li[bullet] for bullet in policy_bullets]],
        ],
        label(class_="flex items-center gap-2")[
            input(name="is_editor", type="checkbox", value="true"),
            "Editor",
        ],
        label(class_="flex items-center gap-2")[
            input(name="is_admin", type="checkbox", value="true"),
            "Admin",
        ],
        button(type="submit")["Create user"],
    ]


def admin_users_page(
    request: Request,
    users: Sequence[User],
    current_user_id: int,
    *,
    error: str | None = None,
    password_errors: list[str] | None = None,
    success: str | None = None,
) -> Element:
    rows: list[dict[str, int | str | bool]] = [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email or "",
            "is_admin": user.is_admin,
            "is_editor": user.is_editor,
            "promote_url": str(request.url_for("promote_user", user_id=user.id)),
            "demote_url": str(request.url_for("demote_user", user_id=user.id)),
            "promote_editor_url": str(
                request.url_for("promote_editor", user_id=user.id)
            ),
            "demote_editor_url": str(request.url_for("demote_editor", user_id=user.id)),
            "delete_account_url": str(
                request.url_for("delete_account", user_id=user.id)
            ),
        }
        for user in users
    ]

    return html_base(
        title="Manage Users",
        request=request,
        body_content=centered_div(
            content=[
                div(class_="flex items-baseline gap-2")[
                    i(data_lucide="users", class_="inline-block"),
                    h1["Manage Users"],
                ],
                hr,
                error_message(error),
                p(class_="text-green-200", role="status")[success] if success else None,
                ul(class_="text-error-main list-disc pl-5")[
                    [li[rule] for rule in password_errors]
                ]
                if password_errors
                else None,
                _create_user_form(),
                hr,
                island(
                    "admin-users",
                    props={
                        "rows": rows,
                        "currentUserId": current_user_id,
                        "pageSize": 25,
                    },
                ),
            ],
            flex=True,
            col=True,
        ),
    )
