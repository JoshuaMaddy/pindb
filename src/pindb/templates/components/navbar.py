"""
htpy page and fragment builders: `templates/components/navbar.py`.
"""

from fastapi import Request
from htpy import Element, a, button, div, form, i, nav

from pindb.database.user import User

_LINK: str = "no-underline text-base-text hover:text-accent"


def _staff_nav_link_items(user: User) -> list[Element]:
    items: list[Element] = [
        a(class_=_LINK, href="/create")["Create"],
        a(class_=_LINK, href="/list")["List"],
        a(class_=_LINK, href="/search/pin")["Search Pin"],
    ]
    if user.is_admin:
        items.append(a(class_=_LINK, href="/admin")["Admin"])
    return items


def _auth_block(user: User | None, *, ml_auto: bool) -> Element:
    cls: str = "flex items-center gap-2" + (" ml-auto" if ml_auto else "")
    if user:
        return div(class_=cls)[
            a(
                class_="no-underline text-base-text hover:text-accent",
                href=f"/user/{user.username}",
            )[user.username],
            form(method="post", action="/auth/logout")[
                button(
                    type="submit",
                    class_="no-underline text-base-text bg-transparent border-0 cursor-pointer p-0 font-inherit hover:text-accent",
                )["Logout"]
            ],
        ]
    return a(
        class_=cls + " no-underline text-base-text",
        href="/auth/login",
    )["Login"]


def navbar(
    request: Request | None = None,
) -> Element:
    user: User | None = getattr(getattr(request, "state", None), "user", None)
    is_staff: bool = bool(user and (user.is_admin or user.is_editor))

    if not is_staff:
        return nav(
            class_="flex flex-wrap items-center gap-x-4 gap-y-1 px-2 py-1 bg-main relative z-10"
        )[
            a(class_="no-underline text-accent font-bold shrink-0", href="/")["PinDB"],
            a(class_=_LINK, href="/list")["List"],
            a(class_=_LINK, href="/search/pin")["Search Pin"],
            _auth_block(user, ml_auto=True),
        ]

    assert user is not None
    return nav(class_="px-2 py-1 bg-main relative z-10")[
        div(
            class_="flex flex-col gap-2 sm:gap-0 w-full",
            x_data="{ open: false }",
            **{
                "@keydown.escape.window": "open = false",
                "@click.outside": "open = false",
            },
        )[
            div(class_="flex items-center gap-3 w-full min-w-0")[
                a(
                    class_="no-underline text-accent font-bold shrink-0",
                    href="/",
                )["PinDB"],
                button(
                    type="button",
                    class_="sm:hidden inline-flex items-center justify-center rounded border border-lightest p-1.5 text-base-text hover:bg-lighter-hover shrink-0",
                    aria_controls="staff-nav-panel",
                    **{
                        "@click": "open = !open",
                        ":aria-expanded": "open",
                        "aria-label": "Toggle navigation",
                    },
                )[i(data_lucide="menu", class_="w-5 h-5")],
                div(
                    class_="hidden sm:flex flex-1 flex-wrap items-center gap-x-4 gap-y-1 min-w-0"
                )[*_staff_nav_link_items(user)],
                div(class_="flex items-center gap-2 shrink-0 ml-auto")[
                    _auth_block(user, ml_auto=False),
                ],
            ],
            div(
                id="staff-nav-panel",
                class_="sm:hidden flex flex-col gap-2 border-t border-lightest pt-2",
                x_show="open",
            )[*_staff_nav_link_items(user)],
        ]
    ]
