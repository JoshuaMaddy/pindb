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
                    i(data_lucide="chevron-right"),
                ]
            )
        else:
            elements.extend(
                [
                    a(href=str(entry[0]))[entry[1]],
                    i(data_lucide="chevron-right"),
                ]
            )

    if len(elements) > 1:
        elements = elements[:-1]

    return div(class_="w-full flex gap-1 mx-auto")[elements]
