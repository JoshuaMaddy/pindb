from typing import Sequence

from fastapi import Request
from htpy import Element, fragment

from pindb.database.material import Material
from pindb.database.pin import Pin
from pindb.templates.base import html_base
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.centered import centered_div
from pindb.templates.components.page_heading import page_heading
from pindb.templates.components.paginated_pin_grid import paginated_pin_grid


def material_page(
    request: Request,
    material: Material,
    pins: Sequence[Pin],
    total_count: int,
    page: int,
    per_page: int,
) -> Element:
    return html_base(
        title=material.name,
        request=request,
        body_content=fragment[
            centered_div(
                content=[
                    bread_crumb(
                        entries=[
                            (request.url_for("get_list_index"), "List"),
                            (request.url_for("get_list_materials"), "Materials"),
                            material.name,
                        ]
                    ),
                    page_heading(
                        icon="anvil",
                        text=material.name.title(),
                        full_width=True,
                    ),
                    paginated_pin_grid(
                        request=request,
                        pins=pins,
                        total_count=total_count,
                        page=page,
                        page_url=str(request.url_for("get_material", id=material.id)),
                        per_page=per_page,
                    ),
                ],
                flex=True,
                col=True,
            )
        ],
    )
