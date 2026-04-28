"""
htpy page and fragment builders: `templates/components/pins/pin_preview_card.py`.
"""

from fastapi import Request
from htpy import Element, a, div, i, span

from pindb.database.pin import Pin
from pindb.templates.components.pins.pin_thumbnail import pin_thumbnail_img
from pindb.templates.pin_image_alt import pin_front_image_alt


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
        class_="pin-3d-card relative grid grid-rows-subgrid row-span-3 gap-0 rounded-lg overflow-clip bg-lighter border border-lightest hover:border-accent"
    )[
        a(
            href=str(
                request.url_for("get_pin", id=pin.id).include_query_params(
                    back=str(request.url)
                )
            ),
            class_="h-full",
        )[
            pin_thumbnail_img(
                request,
                pin.front_image_guid,
                sizes=(
                    # Multi-column grid cells are ~220px wide; cap at 200px so 1x picks 200w
                    # (400w needs sizes >200 CSS px). Still cap vw to avoid 600w on wide tablets.
                    # Narrow single-column: keep min(100vw, 360px) so large phones use 400w.
                    "(min-width: 64rem) min(200px, 22vw), "
                    "(min-width: 40rem) min(45vw, 200px), "
                    "min(100vw, 360px)"
                ),
                alt=pin_front_image_alt(pin),
                class_="object-cover aspect-square w-full",
            )
        ],
        a(
            class_="p-2 text-base-text no-underline flex flex-col gap-0.5",
            href=str(
                request.url_for("get_pin", id=pin.id).include_query_params(
                    back=str(request.url)
                )
            ),
        )[span[("(P) " + pin.name) if pin.is_pending else pin.name],],
        div(class_="p-2")[
            bool(shop_text or artist_text)
            and div(class_="flex flex-col gap-0.5 text-xs **:text-lightest-hover")[
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
