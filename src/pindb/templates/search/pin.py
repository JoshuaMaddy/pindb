"""
htpy page and fragment builders: `templates/search/pin.py`.
"""

from fastapi import Request
from fastapi.datastructures import URL
from htpy import Element, a, div, form, h1, hr, i, input

from pindb.database.user import User
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div


def search_pin_input(
    post_url: URL | str,
    hx_target: str = "#results",
    initial_query: str | None = None,
) -> Element:
    trigger: str = (
        "load, input changed delay:1s" if initial_query else "input changed delay:1s"
    )
    return form(
        hx_post=str(post_url),
        hx_target=hx_target,
        class_="flex flex-col gap-2 [&_label]:font-semibold",
    )[
        div(class_="p-4 rounded-3xl bg-lighter-hover flex items-center justify-center")[
            input(
                type="text",
                name="search",
                id="search",
                value=initial_query or None,
                hx_post=str(post_url),
                hx_target=hx_target,
                hx_trigger=trigger,
                placeholder="Search for a pin",
                class_="bg-none border-0 bg-transparent focus:outline-0 w-full text-lg text-center",
            ),
        ]
    ]


def search_pin_page(
    post_url: URL | str,
    request: Request | None = None,
    initial_query: str | None = None,
) -> Element:
    user: User | None = (
        getattr(getattr(request, "state", None), "user", None) if request else None
    )
    header_extras = (
        user is not None
        and user.is_admin
        and a(
            href="/bulk-edit/from/search",
            class_="inline-flex items-center gap-1 text-sm text-accent hover:underline",
            title="Bulk edit search results",
        )[
            i(data_lucide="layers", class_="w-4 h-4"),
            "Bulk edit results",
        ]
    )
    return html_base(
        title="Search for a Pin",
        request=request,
        body_content=centered_div(
            content=[
                div(
                    class_="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-4",
                )[
                    h1["Search for a Pin"],
                    header_extras,
                ],
                hr,
                search_pin_input(post_url=post_url, initial_query=initial_query),
                div("#results", class_="mt-4"),
            ],
        ),
    )
