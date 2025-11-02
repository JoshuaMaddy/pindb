from fastapi import Request
from htpy import Element, div, h1, hr

from pindb.templates.base import html_base
from pindb.templates.components.card_link import card_link


def list_index(request: Request) -> Element:
    return html_base(
        div(class_="grid grid-cols-2 w-[60ch] mx-auto my-5 gap-2")[
            h1(class_="col-span-2")["List"],
            hr(class_="col-span-2"),
            card_link(
                href=request.url_for("get_list_shops"),
                text="Shop",
                icon="store",
            ),
            card_link(
                href=request.url_for("get_list_materials"),
                text="Material",
                icon="anvil",
            ),
            card_link(
                href=request.url_for("get_list_tags"),
                text="Tag",
                icon="tag",
            ),
            card_link(
                href=request.url_for("get_list_pin_sets"),
                text="Pin Set",
                icon="layout-grid",
            ),
        ]
    )
