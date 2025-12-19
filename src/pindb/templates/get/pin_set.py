from fastapi import Request
from htpy import Element, div, fragment, h1, h2, i, p

from pindb.database.pin_set import PinSet
from pindb.templates.base import html_base
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.centered import centered_div
from pindb.templates.components.pin_grid import pin_grid


def pin_set_page(
    request: Request,
    pin_set: PinSet,
) -> Element:
    return html_base(
        title=pin_set.name,
        body_content=centered_div(
            content=[
                bread_crumb(
                    entries=[
                        (request.url_for("get_list_index"), "List"),
                        (request.url_for("get_list_pin_sets"), "Pin Sets"),
                        pin_set.name,
                    ]
                ),
                div(class_="flex w-full gap-2 items-baseline")[
                    i(data_lucide="layout-grid"),
                    h1[pin_set.name.title()],
                ],
                fragment[bool(pin_set.description) and div[p[pin_set.description]]],
                fragment[
                    bool(len(pin_set.pins)) and h2[f"All Pins ({len(pin_set.pins)})"],
                    pin_grid(
                        request=request,
                        pins=pin_set.pins,
                    ),
                ],
            ],
            flex=True,
            col=True,
        ),
    )
