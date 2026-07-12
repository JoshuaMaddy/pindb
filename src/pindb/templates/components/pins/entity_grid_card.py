"""
htpy page and fragment builders: `templates/components/pins/entity_grid_card.py`.
"""

from typing import Sequence

from fastapi import Request
from htpy import BaseElement, Element, VoidElement, a, div, span

from pindb.database.pin import Pin
from pindb.templates.components.pins.pin_thumbnail import pin_thumbnail_img
from pindb.templates.pin_image_alt import pin_front_image_alt

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
    pins: Sequence[Pin],
    pin_count: int,
    name: str,
    badge: BaseElement | None = None,
    allow_overflow: bool = False,
    name_text_class: str = "text-sm",
    additional_classes: str = "",
) -> Element:
    """Card for one entity: 2×2 thumbnail grid, name, pin count, optional badge.

    ``pins`` is the sample to draw (at most four; see
    ``database.pin_previews.load_pin_previews``) and ``pin_count`` is how many the
    entity actually has. The two are separate because loading every pin just to
    call ``len`` on it is what made the list pages slow.
    """
    images: list[VoidElement | Element] = [
        pin_thumbnail_img(
            request,
            pin.front_image_guid,
            sizes=(
                # 2×2 tile inside the card; cap vw so wide viewports do not pick 600w.
                "(min-width: 64rem) 96px, "
                "(min-width: 40rem) min(24vw, 120px), "
                "min(26vw, 130px)"
            ),
            alt=pin_front_image_alt(pin),
            class_=f"object-cover w-full h-full aspect-square bg-lighter {_CORNER_CLASSES[index]}",
        )
        for index, pin in enumerate(pins[: len(_CORNER_CLASSES)])
    ]
    while len(images) < 4:
        images.append(div(class_=f"bg-lighter {_CORNER_CLASSES[len(images)]}"))

    return a(
        href=href,
        class_=f"no-underline text-base-text rounded-xl overflow-clip bg-main {'max-md:overflow-visible' if allow_overflow else ''} "
        "border border-lightest hover:scale-[102%] hover:border-accent transition-all duration-100 ease-linear flex flex-col relative "
        f"{additional_classes}",
    )[
        div(
            class_="grid grid-cols-2 grid-rows-2 gap-2 w-full aspect-square p-2",
            aria_hidden="true",
        )[*images],
        div(
            class_=f"p-2 {name_text_class} font-medium flex items-center justify-between gap-1"
        )[
            div(class_="min-w-0 wrap-break-word")[
                name,
                # nowrap so a long name breaking across lines cannot also split the
                # count itself into "(2" / "2)".
                span(class_="text-lightest-hover ml-1 whitespace-nowrap")[
                    f"({pin_count})"
                ],
            ],
            badge and badge,
        ],
    ]
