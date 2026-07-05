"""
htpy page and fragment builders: `templates/search/pin.py`.
"""

from fastapi import Request
from htpy import Element, a, div, form, h1, hr, i, input

from pindb.database.pin import Pin
from pindb.database.user import User
from pindb.templates.base import html_base
from pindb.templates.components.display.empty_state import empty_state
from pindb.templates.components.layout.centered import centered_div
from pindb.templates.components.pins.pin_grid import pin_grid

SEARCH_URL = "/search/pin"


def search_pin_input(
    hx_target: str = "#results",
    initial_query: str | None = None,
) -> Element:
    # Live search via GET so the query lands in the URL (bookmarkable, shareable,
    # back-button friendly). Server renders results inline on full loads, so no
    # "load" trigger is needed here.
    return form(
        hx_get=SEARCH_URL,
        hx_target=hx_target,
        hx_push_url="true",
        class_="flex flex-col gap-2 [&_label]:font-semibold",
    )[
        div(class_="p-4 rounded-3xl bg-lighter-hover flex items-center justify-center")[
            input(
                type="search",
                name="q",
                id="search",
                value=initial_query or None,
                hx_get=SEARCH_URL,
                hx_target=hx_target,
                hx_trigger="input changed delay:500ms, search",
                hx_push_url="true",
                placeholder="Search for a pin",
                autocomplete="off",
                class_="bg-none border-0 bg-transparent focus:outline-0 w-full text-lg text-center",
            ),
        ]
    ]


def search_results(
    request: Request,
    pins: list[Pin] | None,
    query: str,
) -> Element:
    """Inner content for the ``#results`` container: grid, empty message, or nothing."""
    if query and not pins:
        return div(class_="mt-4 flex justify-center")[
            empty_state(f"No pins found for “{query}”.")
        ]
    return pin_grid(request=request, pins=pins)


def search_pin_page(
    request: Request | None = None,
    initial_query: str | None = None,
    pins: list[Pin] | None = None,
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
                search_pin_input(initial_query=initial_query),
                div("#results", class_="mt-4")[
                    request is not None
                    and search_results(
                        request=request, pins=pins, query=initial_query or ""
                    )
                ],
            ],
        ),
    )
