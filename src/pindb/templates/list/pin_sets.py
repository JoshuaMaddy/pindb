from typing import Sequence

from fastapi import Request
from htpy import Element, div, p

from pindb.database.pin_set import PinSet
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.card import card
from pindb.templates.components.thumbnail_grid import thumbnail_grid
from pindb.templates.list.base import base_list


def pin_sets_list(
    request: Request,
    pin_sets: Sequence[PinSet],
) -> Element:
    return base_list(
        title="Pin Sets",
        request=request,
        items=[
            card(
                href=request.url_for("get_pin_set", id=set.id),
                content=div(class_="flex gap-2 w-full")[
                    thumbnail_grid(request, set.pins),
                    div[
                        p(class_="text-lg")[set.name],
                        p(class_="text-pin-base-300")[set.description],
                    ],
                ],
            )
            for set in pin_sets
        ],
        bread_crumb=bread_crumb(
            entries=[
                (request.url_for("get_list_index"), "List"),
                "Pin Sets",
            ]
        ),
    )
