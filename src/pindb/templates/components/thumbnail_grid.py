"""
htpy page and fragment builders: `templates/components/thumbnail_grid.py`.
"""

from random import sample
from typing import Sequence

from fastapi import Request
from htpy import Element, VoidElement, div, img

from pindb.database import Pin, PinSet


def thumbnail_grid(
    request: Request,
    pins: PinSet | Sequence[Pin] | set[Pin],
) -> Element:
    if isinstance(pins, PinSet):
        pin_list: list[Pin] = list(pins.pins)
    elif isinstance(pins, set):
        pin_list = list(pins)
    else:
        pin_list = list(pins)

    if len(pin_list) > 4:
        pin_list = sample(pin_list, k=4)

    elements: list[VoidElement | Element] = [
        img(
            src=str(
                request.url_for(
                    "get_image", guid=pin.front_image_guid
                ).include_query_params(thumbnail=True)
            ),
            class_="object-cover aspect-square w-full h-full bg-pin-base-450",
        )
        for pin in pin_list
    ]

    while len(elements) < 4:
        elements.append(div(class_="bg-pin-base-450"))

    return div(
        class_="grid grid-cols-2 grid-rows-2 size-15 gap-0.5 overflow-clip rounded-sm",
        aria_hidden="true",
    )[*elements]
