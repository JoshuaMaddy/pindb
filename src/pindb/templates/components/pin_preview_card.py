from fastapi import Request
from htpy import Element, a, div, img

from pindb.database.pin import Pin


def pin_preview_card(request: Request, pin: Pin) -> Element:
    return div(
        class_="grid grid-rows-subgrid row-span-2 gap-0 rounded-lg overflow-clip bg-blue-300 hover:scale-[102%] "
    )[
        a(
            href=str(request.url_for("get_pin", id=pin.id)),
            class_="h-full",
        )[
            img(
                src=str(request.url_for("get_image", guid=pin.front_image_guid)),
                class_="object-contain h-full",
            )
        ],
        a(
            class_="p-2 text-black no-underline",
            href=str(request.url_for("get_pin", id=pin.id)),
        )[pin.name],
    ]
