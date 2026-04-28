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
from titlecase import titlecase

from pindb.database.user import User
from pindb.database.user_auth_provider import OAuthProvider, UserAuthProvider
from pindb.password_policy import describe_policy
from pindb.templates.base import html_base
from pindb.templates.components.forms.error_message import error_message
from pindb.templates.components.layout.centered import centered_div

_PROVIDER_LABELS = {
    OAuthProvider.google: "Google",
    OAuthProvider.discord: "Discord",
    OAuthProvider.meta: "Meta",
}


def _provider_section(
    *,
    enabled_providers: list[OAuthProvider],
    linked_providers: list[UserAuthProvider],
    can_unlink: bool,
) -> Element:
    linked_by_provider = {link.provider: link for link in linked_providers}
    rows: list[Element] = []
    for provider in enabled_providers:
        label_text = _PROVIDER_LABELS.get(provider, titlecase(provider.value))
        link = linked_by_provider.get(provider)
        if link is not None:
            detail_parts: list[str] = []
            if link.provider_email:
                detail_parts.append(link.provider_email)
            if link.email_verified:
                detail_parts.append("verified")
            detail = f" ({', '.join(detail_parts)})" if detail_parts else ""
            rows.append(
                li(class_="flex items-center justify-between gap-2")[
                    div[f"{label_text}{detail}"],
                    form(
                        method="post",
                        action=f"/user/me/unlink/{provider.value}",
                    )[
                        button(
                            type="submit",
                            disabled=not can_unlink,
                            class_="text-sm",
                        )["Unlink"],
                    ],
                ]
            )
        else:
            rows.append(
                li(class_="flex items-center justify-between gap-2")[
                    div[label_text],
                    a(
                        href=f"/auth/{provider.value}?link=1",
                        class_="text-sm",
                    )["Link account"],
                ]
            )
    return ul(class_="flex flex-col gap-2")[rows]


def security_page(
    request: Request,
    *,
    current_user: User,
    linked_providers: list[UserAuthProvider],
    enabled_providers: list[OAuthProvider],
    error: str | None = None,
    success: str | None = None,
    password_errors: list[str] | None = None,
) -> Element:
    policy = describe_policy()
    has_password = current_user.hashed_password is not None
    can_unlink = has_password or len(linked_providers) > 1

    return html_base(
        title="Security",
        request=request,
        body_content=centered_div(
            content=[
                h1["Security settings"],
                hr,
                error_message(error),
                p(class_="text-green-200")[success] if success else None,
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
                    ),
                    label(for_="confirm_password")["Confirm new password"],
                    input(
                        id="confirm_password",
                        name="confirm_password",
                        type="password",
                        required=True,
                        autocomplete="new-password",
                        minlength=str(policy.min_length),
                    ),
                    div(class_="text-sm text-subtle")[
                        ul(class_="list-disc pl-5")[
                            [li[bullet] for bullet in policy.bullets()]
                        ],
                    ],
                    button(type="submit")[
                        "Set password" if not has_password else "Change password"
                    ],
                ],
                hr,
                h2["Sign-in providers"],
                _provider_section(
                    enabled_providers=enabled_providers,
                    linked_providers=linked_providers,
                    can_unlink=can_unlink,
                )
                if enabled_providers
                else p(class_="text-subtle")[
                    "No OAuth providers are configured on this server."
                ],
                div(class_="mt-4")[
                    a(href=f"/user/{current_user.username}")["Back to profile"],
                ],
            ],
            flex=True,
            col=True,
        ),
    )
