from fastapi import Request
from htpy import Element, Fragment, div, fragment, h1, hr

from pindb.templates.base import html_base
from pindb.templates.components.card import card
from pindb.templates.components.centered import centered_div


def list_index(request: Request) -> Fragment:
    return fragment[
        card(
            href=request.url_for("get_list_shops"),
            content="Shops",
            icon="store",
        ),
        card(
            href=request.url_for("get_list_materials"),
            content="Materials",
            icon="anvil",
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
    ]


def list_index_page(request: Request) -> Element:
    return html_base(
        title="List",
        request=request,
        body_content=centered_div(
            content=[
                div(class_="min-md:col-span-2")[
                    h1(class_="col-span-2")["List"],
                    hr(class_="col-span-2"),
                ],
                list_index(request=request),
            ],
            additional_classes="grid min-md:grid-cols-2",
            content_width="small",
        ),
    )
