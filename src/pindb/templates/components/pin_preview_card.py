from fastapi import Request
from htpy import Element, a, div, i, img, span

from pindb.database.pin import Pin


def pin_preview_card(
    request: Request,
    pin: Pin,
) -> Element:
    shops = sorted(pin.shops, key=lambda shop: shop.name)
    artists = sorted(pin.artists, key=lambda artist: artist.name)
    shop_text: str | None = (
        (
            (("(P) " + shops[0].name) if shops[0].is_pending else shops[0].name)
            + (" …" if len(shops) > 1 else "")
        )
        if shops
        else None
    )
    artist_text: str | None = (
        (
            (("(P) " + artists[0].name) if artists[0].is_pending else artists[0].name)
            + (" …" if len(artists) > 1 else "")
        )
        if artists
        else None
    )
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
                        "get_image",
                        guid=pin.front_image_guid,
                    ).include_query_params(thumbnail=True)
                ),
                class_="object-cover h-full",
            )
        ],
        a(
            class_="p-2 text-pin-base-text no-underline flex flex-col gap-0.5",
            href=str(request.url_for("get_pin", id=pin.id)),
        )[
            span[("(P) " + pin.name) if pin.is_pending else pin.name],
            bool(shop_text or artist_text)
            and div(class_="flex flex-col gap-0.5 text-xs **:text-pin-base-300")[
                bool(shop_text)
                and div(class_="flex gap-0.5")[
                    i(data_lucide="store", class_="size-4"),
                    shop_text,
                ],
                bool(artist_text)
                and div(class_="flex gap-0.5")[
                    i(data_lucide="palette", class_="size-4"),
                    artist_text,
                ],
            ],
        ],
    ]
