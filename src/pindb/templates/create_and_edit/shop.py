"""
htpy page and fragment builders: `templates/create_and_edit/shop.py`.
"""

from fastapi import Request
from fastapi.datastructures import URL
from htpy import Element

from pindb.database.shop import Shop
from pindb.templates.create_and_edit._simple_aliased_entity import (
    simple_aliased_entity_form,
)


def shop_form(
    post_url: URL | str,
    request: Request,
    shop: Shop | None = None,
) -> Element:
    return simple_aliased_entity_form(
        post_url=post_url,
        request=request,
        entity=shop,
        entity_kind="Shop",
        create_icon="store",
        create_article="a",
    )
