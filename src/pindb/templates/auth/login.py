from fastapi import Request
from htpy import (
    Element,
    a,
    button,
    div,
    form,
    h1,
    hr,
    img,
    input,
    label,
    span,
)

from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div
from pindb.templates.components.error_message import error_message


def _oauth_link(
    *,
    href: str,
    label: str,
    icon_slug: str,
    bg_hover: str,
) -> Element:
    return a(
        href=href,
        class_=(
            "flex w-full items-center justify-center gap-3 rounded-lg px-4 py-2.5 "
            "text-sm font-medium text-white shadow-sm transition "
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40 no-underline "
            f"{bg_hover}"
        ),
    )[
        img(
            src=f"https://cdn.simpleicons.org/{icon_slug}/ffffff",
            alt="",
            width="20",
            height="20",
            class_="h-5 w-5 shrink-0",
            loading="lazy",
            aria_hidden="true",
        ),
        span(class_="no-underline")[label],
    ]


def login_page(
    request: Request,
    error: str | None = None,
    *,
    google_enabled: bool = False,
    discord_enabled: bool = False,
    meta_enabled: bool = False,
) -> Element:
    oauth_rows: list[Element] = []
    if google_enabled:
        oauth_rows.append(
            _oauth_link(
                href="/auth/google",
                label="Continue with Google",
                icon_slug="google",
                bg_hover="bg-[#4285F4] hover:bg-[#3367d6]",
            )
        )
    if discord_enabled:
        oauth_rows.append(
            _oauth_link(
                href="/auth/discord",
                label="Continue with Discord",
                icon_slug="discord",
                bg_hover="bg-[#5865F2] hover:bg-[#4752c4]",
            )
        )
    if meta_enabled:
        oauth_rows.append(
            _oauth_link(
                href="/auth/meta",
                label="Continue with Meta",
                icon_slug="meta",
                bg_hover="bg-[#0467DF] hover:bg-[#0356b8]",
            )
        )

    oauth_any = bool(oauth_rows)
    oauth_block: Element | None = (
        div(class_="flex w-full flex-col gap-2")[oauth_rows] if oauth_rows else None
    )

    email_divider: Element | None = (
        div(class_="my-5 flex w-full items-center gap-3")[
            hr(class_="flex-1 border-pin-base-400"),
            span(class_="shrink-0 text-sm text-subtle")["or continue with email"],
            hr(class_="flex-1 border-pin-base-400"),
        ]
        if oauth_any
        else None
    )

    return html_base(
        title="Login",
        request=request,
        body_content=centered_div(
            content_width="small",
            content=[
                h1["Login"],
                hr,
                oauth_block,
                email_divider,
                error_message(error),
                form(
                    method="post",
                    action="/auth/login",
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
                div(class_="mt-4 text-center")[
                    "Don't have an account? ",
                    a(href="/auth/signup")["Sign up"],
                ],
            ],
            flex=True,
            col=True,
        ),
    )
