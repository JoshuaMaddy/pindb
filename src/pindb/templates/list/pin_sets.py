from typing import Sequence

from fastapi import Request
from htpy import Element, a

from pindb.database.pin_set import PinSet
from pindb.templates.list.base import base_list


def pin_sets_list(request: Request, pin_sets: Sequence[PinSet]) -> Element:
    return base_list(
        title="Pin Sets",
        items=[
            a(href=str(request.url_for("get_pin_set", id=pin_set.id)))[pin_set.name]
            for pin_set in pin_sets
        ],
    )
