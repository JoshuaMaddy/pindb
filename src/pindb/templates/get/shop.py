from fastapi import Request
from htpy import Element, a, br, div, fragment, h1, h2, i, p

from pindb.database import Shop
from pindb.templates.base import html_base
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.centered import centered_div
from pindb.templates.components.pin_grid import pin_grid


def shop_page(
    request: Request,
    shop: Shop,
) -> Element:
    return html_base(
        title=shop.name,
        body_content=centered_div(
            content=fragment[
                bread_crumb(
                    [
                        (request.url_for("get_list_index"), "List"),
                        (request.url_for("get_list_shops"), "Shops"),
                        shop.name,
                    ]
                ),
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
            ],
            flex=True,
            col=True,
        ),
    )
