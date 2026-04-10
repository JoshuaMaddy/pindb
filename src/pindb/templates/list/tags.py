from typing import Sequence

from fastapi import Request
from htpy import Element, div, p

from pindb.database.tag import Tag
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.card import card
from pindb.templates.components.thumbnail_grid import thumbnail_grid
from pindb.templates.list.base import base_list


def tags_list(
    request: Request,
    tags: Sequence[Tag],
) -> Element:
    return base_list(
        title="Tags",
        request=request,
        items=[
            card(
                href=request.url_for("get_tag", id=tag.id),
                content=div(class_="flex gap-2 w-full")[
                    thumbnail_grid(request, tag.pins),
                    p(class_="text-lg")[tag.name],
                ],
            )
            for tag in tags
        ],
        bread_crumb=bread_crumb(
            entries=[
                (request.url_for("get_list_index"), "List"),
                "Tags",
            ]
        ),
    )
