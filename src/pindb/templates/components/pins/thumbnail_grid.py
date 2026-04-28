"""
htpy page and fragment builders: `templates/components/pins/thumbnail_grid.py`.
"""

from random import sample
from typing import Sequence, cast

from fastapi import Request
from htpy import Element, VoidElement, div

from pindb.database import Pin, PinSet
from pindb.templates.components.pins.pin_thumbnail import pin_thumbnail_img
from pindb.templates.pin_image_alt import pin_front_image_alt


def thumbnail_grid(
    request: Request,
    pins: PinSet | Sequence[Pin] | set[Pin],
) -> Element:
    if isinstance(pins, PinSet):
        pin_list: list[Pin] = list(pins.pins)
    elif isinstance(pins, set):
        pin_list = list(cast(set[Pin], pins))
    else:
        pin_list = list(pins)

    if len(pin_list) > 4:
        pin_list = sample(pin_list, k=4)

    elements: list[VoidElement | Element] = [
        pin_thumbnail_img(
            request,
            pin.front_image_guid,
            sizes="(min-width: 64rem) 30px, (min-width: 40rem) 6vw, 30px",
            alt=pin_front_image_alt(pin),
            class_="object-cover aspect-square w-full h-full bg-lighter",
        )
        for pin in pin_list
    ]

    while len(elements) < 4:
        elements.append(div(class_="bg-lighter"))

    return div(
        class_="grid grid-cols-2 grid-rows-2 size-15 gap-0.5 overflow-clip rounded-sm",
        aria_hidden="true",
    )[*elements]
