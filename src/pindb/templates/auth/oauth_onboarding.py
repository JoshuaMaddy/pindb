from fastapi import Request
from htpy import (
    Element,
    button,
    div,
    form,
    h1,
    hr,
    input,
    label,
    p,
)

from pindb.database.user_auth_provider import OAuthProvider
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div
from pindb.templates.components.error_message import error_message

_PROVIDER_LABELS = {
    OAuthProvider.google: "Google",
    OAuthProvider.discord: "Discord",
    OAuthProvider.meta: "Meta",
}


def oauth_onboarding_page(
    request: Request,
    *,
    provider: OAuthProvider,
    suggested_username: str,
    email: str | None,
    error: str | None = None,
) -> Element:
    provider_label = _PROVIDER_LABELS.get(provider, provider.value.title())

    return html_base(
        title="Choose Username",
        request=request,
        body_content=centered_div(
            content=[
                h1["Finish signing up"],
                hr,
                p[
                    "We've verified your ",
                    provider_label,
                    " account",
                    f" ({email})" if email else "",
                    ". Pick a username to complete signup — we've suggested ",
                    "one you can keep or change.",
                ],
                error_message(error),
                form(
                    method="post",
                    action="/auth/oauth/onboarding",
                    class_="flex flex-col gap-2",
                )[
                    label(for_="username")["Username"],
                    input(
                        id="username",
                        name="username",
                        type="text",
                        required=True,
                        autocomplete="username",
                        value=suggested_username,
                        minlength="1",
                        maxlength="50",
                    ),
                    button(type="submit")["Create account"],
                ],
                div(class_="mt-4 text-subtle text-sm")[
                    "You can always add or remove sign-in methods later from "
                    "your security settings."
                ],
            ],
            flex=True,
            col=True,
        ),
    )
