from fastapi import Request
from htpy import Element, a, div, img

from pindb.database.pin import Pin


def pin_preview_card(request: Request, pin: Pin) -> Element:
    return div(
        class_="grid grid-rows-subgrid row-span-2 gap-0 rounded-lg overflow-clip bg-pin-base-450 border border-pin-base-400 hover:scale-[102%] hover:border-accent"
    )[
        a(
            href=str(request.url_for("get_pin", id=pin.id)),
            class_="h-full",
        )[
            img(
                src=str(
                    request.url_for(
                        "get_image", guid=pin.front_image_guid
                    ).include_query_params(thumbnail=True)
                ),
                class_="object-contain h-full",
            )
        ],
        a(
            class_="p-2 text-pin-base-text no-underline",
            href=str(request.url_for("get_pin", id=pin.id)),
        )[pin.name],
    ]
