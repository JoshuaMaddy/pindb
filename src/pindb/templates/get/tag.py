from fastapi import Request
from htpy import div, fragment, h1, h2, i

from pindb.database.tag import Tag
from pindb.templates.base import html_base
from pindb.templates.components.pin_grid import pin_grid


def tag_page(
    request: Request,
    tag: Tag,
):
    return html_base(
        body_content=fragment[
            div(class_="max-w-[80ch] mx-auto bg-blue-200 p-10 flex flex-col gap-2")[
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
        ],
    )
