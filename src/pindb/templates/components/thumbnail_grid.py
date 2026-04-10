from random import sample
from typing import Sequence

from fastapi import Request
from htpy import Element, VoidElement, div, img

from pindb.database import Pin, PinSet


def thumbnail_grid(
    request: Request,
    pins: PinSet | Sequence[Pin] | set[Pin],
) -> Element:
    if isinstance(pins, set):
        if len(pins) <= 4:
            pins: list[Pin] = list(pins)  # ty:ignore[invalid-argument-type, invalid-assignment]
        else:
            pins: list[Pin] = sample(list(pins), k=4)
    elif isinstance(pins, PinSet):
        if len(pins.pins) >= 5:
            pins = pins.pins
        else:
            pins: list[Pin] = sample(pins.pins, k=4)
    elif len(pins) >= 5:
        pins: list[Pin] = sample(pins, k=4)

    elements: list[VoidElement | Element] = [
        img(
            src=str(
                request.url_for(
                    "get_image", guid=pin.front_image_guid
                ).include_query_params(thumbnail=True)
            ),
            class_="object-contain h-full",
        )
        for pin in pins
    ]

    while len(elements) < 4:
        elements.append(div(class_="bg-black opacity-20"))

    return div(
        class_="grid grid-cols-2 grid-rows-2 size-15 gap-0.5 overflow-clip rounded-sm"
    )[*elements]
