from typing import Sequence

from fastapi import Request
from htpy import Element, a

from pindb.database.material import Material
from pindb.templates.list.base import base_list


def materials_list(request: Request, materials: Sequence[Material]) -> Element:
    return base_list(
        title="Materials",
        items=[
            a(href=str(request.url_for("get_material", id=material.id)))[material.name]
            for material in materials
        ],
    )
