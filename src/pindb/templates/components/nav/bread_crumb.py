"""
htpy page and fragment builders: `templates/components/nav/bread_crumb.py`.
"""

from fastapi.datastructures import URL
from htpy import Element, a, div, i, p

BreadCrumbLink = tuple[URL | str, str]


def bread_crumb(entries: list[BreadCrumbLink | str] | None) -> Element | None:
    if entries is None:
        return

    elements: list[Element] = list()

    for entry in entries:
        if isinstance(entry, str):
            elements.extend(
                [
                    p[entry],
                    i(data_lucide="chevron-right", aria_hidden="true"),
                ]
            )
        else:
            elements.extend(
                [
                    a(href=str(entry[0]))[entry[1]],
                    i(data_lucide="chevron-right", aria_hidden="true"),
                ]
            )

    if len(elements) > 1:
        elements: list[Element] = elements[:-1]

    return div(class_="w-full flex flex-wrap items-center gap-x-1 gap-y-0.5 mx-auto")[
        elements
    ]
