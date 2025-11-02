from fastapi import Request
from htpy import a, br, div, fragment, h1, h2, i, p

from pindb.database import Shop
from pindb.templates.base import html_base
from pindb.templates.components.pin_grid import pin_grid


def shop_page(
    request: Request,
    shop: Shop,
):
    return html_base(
        body_content=fragment[
            div(class_="mx-auto bg-blue-200 p-10 flex flex-col gap-2 max-w-[120ch]")[
                div(class_="flex w-full gap-2 items-baseline")[
                    i(data_lucide="store"),
                    h1[shop.name],
                ],
                fragment[shop.description and div[p[shop.description]]],
                fragment[
                    bool(len(shop.links))
                    and div[
                        h2["Links"],
                        *[
                            fragment[a(href=link.path)[link.path], br]
                            for link in shop.links
                        ],
                    ]
                ],
                fragment[
                    bool(len(shop.pins)) and h2[f"All Pins ({len(shop.pins)})"],
                    pin_grid(
                        request=request,
                        pins=shop.pins,
                    ),
                ],
            ]
        ],
    )
