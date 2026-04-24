"""
htpy page and fragment builders: `templates/components/entity_grid_card.py`.
"""

from random import sample
from typing import Sequence

from fastapi import Request
from htpy import BaseElement, Element, VoidElement, a, div, img, span

from pindb.database.pin import Pin

# Grid is 2×2; corners flow left-to-right, top-to-bottom.
_CORNER_CLASSES: list[str] = [
    "rounded-tl-lg",  # index 0 — top-left
    "rounded-tr-lg",  # index 1 — top-right
    "rounded-bl-lg",  # index 2 — bottom-left
    "rounded-br-lg",  # index 3 — bottom-right
]


def entity_grid_card(
    request: Request,
    href: str,
    pins: Sequence[Pin] | set[Pin],
    name: str,
    badge: BaseElement | None = None,
) -> Element:
    pin_list: list[Pin] = list(pins)
    pin_count: int = len(pin_list)
    if len(pin_list) > 4:
        pin_list = sample(population=pin_list, k=4)

    images: list[VoidElement | Element] = [
        img(
            src=str(
                request.url_for(
                    "get_image",
                    guid=pin.front_image_guid,
                ).include_query_params(thumbnail=True)
            ),
            class_=f"object-cover w-full h-full {_CORNER_CLASSES[index]}",
        )
        for index, pin in enumerate(pin_list)
    ]
    while len(images) < 4:
        images.append(div(class_=f"bg-pin-base-450 {_CORNER_CLASSES[len(images)]}"))

    return a(
        href=href,
        class_="no-underline text-pin-base-text rounded-xl overflow-clip bg-pin-main "
        "border border-pin-base-350 hover:scale-[102%] hover:border-accent flex flex-col",
    )[
        div(
            class_="grid grid-cols-2 grid-rows-2 gap-2 w-full aspect-square p-2",
            aria_hidden="true",
        )[*images],
        div(class_="p-2 text-sm font-medium flex items-center justify-between gap-1")[
            div[
                name,
                span(class_="text-pin-base-300 ml-1")[f"({pin_count})"],
            ],
            badge or "",
        ],
    ]
