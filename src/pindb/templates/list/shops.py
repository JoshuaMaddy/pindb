from typing import Sequence

from fastapi import Request
from htpy import Element, a

from pindb.database.shop import Shop
from pindb.templates.list.base import base_list


def shops_list(request: Request, shops: Sequence[Shop]) -> Element:
    return base_list(
        title="Shops",
        items=[
            a(href=str(request.url_for("get_shop", id=shop.id)))[shop.name]
            for shop in shops
        ],
    )
