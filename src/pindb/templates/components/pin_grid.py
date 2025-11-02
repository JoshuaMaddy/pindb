from typing import Iterable

from fastapi import Request
from htpy import Element, div

from pindb.database.pin import Pin
from pindb.templates.components.pin_preview_card import pin_preview_card


def pin_grid(request: Request, pins: Iterable[Pin]) -> Element:
    return div(
        class_="grid grid-cols-[repeat(auto-fill,_minmax(128px,_1fr))] auto auto-rows-[1fr_max-content] gap-3"
    )[*[pin_preview_card(request=request, pin=pin) for pin in pins]]
