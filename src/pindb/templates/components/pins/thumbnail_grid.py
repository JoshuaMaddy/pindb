"""
htpy page and fragment builders: `templates/components/pins/thumbnail_grid.py`.
"""

from typing import Sequence

from fastapi import Request
from htpy import Element, VoidElement, div

from pindb.database import Pin
from pindb.templates.components.pins.pin_thumbnail import pin_thumbnail_img
from pindb.templates.pin_image_alt import pin_front_image_alt

_TILES: int = 4


def thumbnail_grid(
    request: Request,
    pins: Sequence[Pin],
) -> Element:
    """2×2 thumbnail tile for an entity, padded with blanks when short.

    ``pins`` is already the sample to draw — callers get it from
    ``database.pin_previews.load_pin_previews`` rather than passing a whole
    relationship collection.
    """
    elements: list[VoidElement | Element] = [
        pin_thumbnail_img(
            request,
            pin.front_image_guid,
            sizes="(min-width: 64rem) 30px, (min-width: 40rem) 6vw, 30px",
            alt=pin_front_image_alt(pin),
            class_="object-cover aspect-square w-full h-full bg-lighter",
        )
        for pin in pins[:_TILES]
    ]

    while len(elements) < _TILES:
        elements.append(div(class_="bg-lighter"))

    return div(
        class_="grid grid-cols-2 grid-rows-2 size-15 gap-0.5 overflow-clip rounded-sm",
        aria_hidden="true",
    )[*elements]
