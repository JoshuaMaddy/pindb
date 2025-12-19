from fastapi import Request
from htpy import Element, Fragment, div, fragment, h1, hr

from pindb.templates.base import html_base
from pindb.templates.components.card_link import card_link
from pindb.templates.components.centered import centered_div


def list_index(request: Request, header: bool = True) -> Fragment:
    return fragment[
        card_link(
            href=request.url_for("get_list_shops"),
            text="Shops",
            icon="store",
        ),
        card_link(
            href=request.url_for("get_list_materials"),
            text="Materials",
            icon="anvil",
        ),
        card_link(
            href=request.url_for("get_list_tags"),
            text="Tags",
            icon="tag",
        ),
        card_link(
            href=request.url_for("get_list_pin_sets"),
            text="Pin Sets",
            icon="layout-grid",
        ),
    ]


def list_index_page(request: Request) -> Element:
    return html_base(
        title="List",
        body_content=centered_div(
            content=[
                div(class_="col-span-2")[
                    h1(class_="col-span-2")["List"],
                    hr(class_="col-span-2"),
                ],
                list_index(request=request),
            ],
            class_="grid grid-cols-2",
        ),
    )
