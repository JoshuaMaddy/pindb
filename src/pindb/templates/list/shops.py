from typing import Sequence

from fastapi import Request
from htpy import Element, div, p

from pindb.database.shop import Shop
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.card import card
from pindb.templates.components.thumbnail_grid import thumbnail_grid
from pindb.templates.list.base import base_list


def shops_list(
    request: Request,
    shops: Sequence[Shop],
) -> Element:
    return base_list(
        title="Shops",
        request=request,
        items=[
            card(
                href=request.url_for("get_shop", id=shop.id),
                content=[
                    thumbnail_grid(request, shop.pins),
                    div[
                        p(class_="text-lg")[shop.name],
                        p(class_="text-pin-base-300")[shop.description],
                    ],
                ],
            )
            for shop in shops
        ],
        bread_crumb=bread_crumb(
            entries=[
                (request.url_for("get_list_index"), "List"),
                "Shops",
            ]
        ),
    )
