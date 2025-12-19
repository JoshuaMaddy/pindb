from fastapi import Request
from htpy import Element, div, fragment, h1, h2, i

from pindb.database.tag import Tag
from pindb.templates.base import html_base
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.centered import centered_div
from pindb.templates.components.pin_grid import pin_grid


def tag_page(
    request: Request,
    tag: Tag,
) -> Element:
    return html_base(
        title=tag.name,
        body_content=centered_div(
            content=fragment[
                bread_crumb(
                    entries=[
                        (request.url_for("get_list_index"), "List"),
                        (request.url_for("get_list_tags"), "Tags"),
                        tag.name,
                    ]
                ),
                div(class_="flex w-full gap-2 items-baseline")[
                    i(data_lucide="tag"),
                    h1[tag.name],
                ],
                fragment[
                    bool(len(tag.pins)) and h2["All Pins"],
                    pin_grid(
                        request=request,
                        pins=tag.pins,
                    ),
                ],
            ],
            flex=True,
            col=True,
        ),
    )
