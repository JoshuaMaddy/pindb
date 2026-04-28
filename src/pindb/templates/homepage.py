"""
htpy page and fragment builders: `templates/homepage.py`.
"""

from fastapi import Request
from htpy import (
    Element,
    Fragment,
    a,
    div,
    form,
    fragment,
    h1,
    h2,
    img,
    input,
    link,
    script,
    span,
)

from pindb.asset_cache_buster import STATIC_CACHE_BUSTER
from pindb.database.pin import Pin
from pindb.templates.base import html_base
from pindb.templates.components.card import card


def _masonry_pin_card(request: Request, pin: Pin) -> Element:
    shops = sorted(pin.shops, key=lambda shop: shop.name)
    artists = sorted(pin.artists, key=lambda artist: artist.name)
    shop_text: str | None = shops[0].name if shops else None
    artist_text: str | None = artists[0].name if artists else None
    return a(
        class_="masonry-pin-card pin-3d-card",
        href=str(request.url_for("get_pin", id=pin.id)),
        tabindex="-1",
        aria_hidden="true",
    )[
        img(
            src=str(
                request.url_for(
                    "get_image", guid=pin.front_image_guid
                ).include_query_params(thumbnail=True)
            ),
            alt="",
            loading="lazy",
            class_="masonry-pin-img",
        ),
        div(class_="masonry-pin-info")[
            span(class_="masonry-pin-name")[pin.name],
            (shop_text or artist_text)
            and div(class_="masonry-pin-meta")[
                shop_text and span[shop_text],
                shop_text and artist_text and " · ",
                artist_text and span[artist_text],
            ],
        ],
    ]


def _masonry_bg(request: Request, pins: list[Pin]) -> Element:
    columns: int = 7
    column_pins: list[list[Pin]] = [[] for _ in range(columns)]
    for idx, pin in enumerate(pins):
        column_pins[idx % columns].append(pin)
    return div(id="pindb-masonry-bg", aria_hidden="true")[
        [
            div(class_="masonry-col")[
                div(class_="masonry-col-inner")[
                    [_masonry_pin_card(request=request, pin=pin) for pin in col]
                ]
            ]
            for col in column_pins
        ]
    ]


def _homepage_center(request: Request) -> Element:
    return div(id="homepage-center")[
        div(id="homepage-card")[
            h1(class_="text-center text-accent")["PinDB"],
            h2(class_="text-center")["A database for all things pins."],
            form(
                id="homepage-search",
                action=str(request.url_for("get_search_pin")),
                method="get",
                class_="flex flex-col gap-2",
            )[
                div(
                    class_="p-4 rounded-3xl bg-lighter flex items-center justify-center border-lightest border"
                )[
                    input(
                        type="text",
                        name="q",
                        placeholder="Search for a pin",
                        autocomplete="off",
                        aria_label="Search for a pin",
                        class_="bg-none border-0 bg-transparent focus:outline-0 w-full text-lg text-center",
                    ),
                ],
            ],
            div(class_="grid grid-cols-2 gap-2")[
                card(
                    href=request.url_for("get_list_shops"),
                    content="Shops",
                    icon="store",
                ),
                card(
                    href=request.url_for("get_list_tags"),
                    content="Tags",
                    icon="tag",
                ),
                card(
                    href=request.url_for("get_list_pin_sets"),
                    content="Pin Sets",
                    icon="layout-grid",
                ),
                card(
                    href=request.url_for("get_list_artists"),
                    content="Artists",
                    icon="palette",
                ),
            ],
        ]
    ]


def _head_extras() -> Fragment:
    return fragment[
        link(
            rel="stylesheet",
            href=f"/static/homepage.css?v={STATIC_CACHE_BUSTER}",
        ),
        script(
            src=f"/static/homepage.js?v={STATIC_CACHE_BUSTER}",
            defer=True,
        ),
    ]


def homepage(request: Request, pins: list[Pin]) -> Element:
    return html_base(
        title="Home",
        request=request,
        head_content=_head_extras(),
        body_content=fragment[
            _masonry_bg(request=request, pins=pins),
            div(id="pindb-cursor-glow", aria_hidden="true"),
            _homepage_center(request=request),
        ],
    )
