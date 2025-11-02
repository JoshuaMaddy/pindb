from fastapi import Request
from htpy import Element, div, h1, hr

from pindb.templates.base import html_base
from pindb.templates.components.card_link import card_link


def create_index(request: Request) -> Element:
    return html_base(
        div(class_="grid grid-cols-2 w-[60ch] mx-auto my-5 gap-2")[
            h1(class_="col-span-2")["Create"],
            hr(class_="col-span-2"),
            card_link(
                href=request.url_for("get_create_pin"),
                text="Pin",
                icon="square-star",
            ),
            card_link(
                href=request.url_for("get_create_shop"),
                text="Shop",
                icon="store",
            ),
            card_link(
                href=request.url_for("get_create_material"),
                text="Material",
                icon="anvil",
            ),
            card_link(
                href=request.url_for("get_create_tag"),
                text="Tag",
                icon="tag",
            ),
            card_link(
                href=request.url_for("get_create_pin_set"),
                text="Pin Set",
                icon="layout-grid",
            ),
        ]
    )
