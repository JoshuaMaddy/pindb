from fastapi import Request
from htpy import a, br, div, fragment, h1, h2, p

from pindb.database import Shop
from pindb.templates.base import html_base


def shop_page(
    request: Request,
    shop: Shop,
):
    return html_base(
        body_content=fragment[
            div(class_="max-w-[80ch] mx-auto bg-blue-200 p-10")[
                h1(class_="text-xl font-bold")[shop.name],
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
            ]
        ],
    )
