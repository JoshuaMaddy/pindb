from fastapi import Request
from htpy import Element, div, h1, hr

from pindb.templates.base import html_base
from pindb.templates.components.card_link import card_link
from pindb.templates.components.centered import centered_div


def create_index(request: Request) -> Element:
    return html_base(
        title="Create",
        body_content=centered_div(
            content=[
                div(class_="col-span-2")[
                    h1["Create"],
                    hr,
                ],
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
                card_link(
                    href=request.url_for("get_create_artist"),
                    text="Artist",
                    icon="palette",
                ),
                div(class_="col-span-2")[hr],
                div(class_="col-span-2 grid")[
                    card_link(
                        href=request.url_for("get_bulk_pin"),
                        text="Bulk Import Pins",
                        icon="table-2",
                    ),
                ],
            ],
            class_="grid grid-cols-2",
        )
    )
