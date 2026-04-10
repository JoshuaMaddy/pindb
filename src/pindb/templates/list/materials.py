from typing import Sequence

from fastapi import Request
from htpy import Element, p

from pindb.database.material import Material
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.card import card
from pindb.templates.components.thumbnail_grid import thumbnail_grid
from pindb.templates.list.base import base_list


def materials_list(
    request: Request,
    materials: Sequence[Material],
) -> Element:
    return base_list(
        title="Materials",
        request=request,
        items=[
            card(
                href=request.url_for("get_material", id=material.id),
                content=[
                    thumbnail_grid(request, material.pins),
                    p(class_="text-lg")[material.name],
                ],
            )
            for material in materials
        ],
        bread_crumb=bread_crumb(
            entries=[
                (request.url_for("get_list_index"), "List"),
                "Materials",
            ]
        ),
    )
