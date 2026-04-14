from fastapi import Request
from htpy import Element, a, button, div, form, nav

from pindb.database.user import User


def navbar(
    request: Request | None = None,
) -> Element:
    user: User | None = getattr(getattr(request, "state", None), "user", None)

    if user:
        auth_link: Element = div(class_="ml-auto flex items-center gap-2")[
            a(
                class_="no-underline text-pin-base-100 hover:text-accent",
                href=f"/user/{user.username}",
            )[user.username],
            form(method="post", action="/auth/logout")[
                button(
                    type="submit",
                    class_="no-underline text-pin-base-100 bg-transparent border-0 cursor-pointer p-0 font-inherit hover:text-accent",
                )["Logout"]
            ],
        ]
    else:
        auth_link: Element = a(
            class_="ml-auto no-underline text-pin-base-100",
            href="/auth/login",
        )["Login"]

    return nav(class_="flex gap-4 px-2 py-1 bg-pin-base-500")[
        a(class_="no-underline text-accent font-bold", href="/")["PinDB"],
        user
        and (user.is_admin or user.is_editor)
        and a(class_="no-underline text-pin-base-100", href="/create")["Create"],
        a(class_="no-underline text-pin-base-100", href="/list")["List"],
        a(class_="no-underline text-pin-base-100", href="/search/pin")["Search Pin"],
        user
        and user.is_admin
        and a(class_="no-underline text-pin-base-100", href="/admin")["Admin"],
        auth_link,
    ]
