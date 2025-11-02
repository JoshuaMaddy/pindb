from fastapi import Request
from htpy import div, fragment, h1, h2, i, p

from pindb.database.pin_set import PinSet
from pindb.templates.base import html_base
from pindb.templates.components.pin_grid import pin_grid


def pin_set_page(
    request: Request,
    pin_set: PinSet,
):
    return html_base(
        body_content=div(
            class_="max-w-[80ch] mx-auto bg-blue-200 p-10 flex flex-col gap-2"
        )[
            div(class_="flex w-full gap-2 items-baseline")[
                i(data_lucide="layout-grid"),
                h1[pin_set.name.title()],
            ],
            pin_set.description and div[p[pin_set.description]],
            fragment[
                bool(len(pin_set.pins)) and h2[f"All Pins ({len(pin_set.pins)})"],
                pin_grid(
                    request=request,
                    pins=pin_set.pins,
                ),
            ],
        ],
    )
