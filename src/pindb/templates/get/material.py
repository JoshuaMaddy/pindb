from fastapi import Request
from htpy import Element, div, fragment, h1, i

from pindb.database.material import Material
from pindb.templates.base import html_base
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.centered import centered_div


def material_page(
    request: Request,
    material: Material,
) -> Element:
    return html_base(
        title=material.name,
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
                    div(class_="flex w-full gap-2 items-baseline")[
                        i(data_lucide="anvil"),
                        h1[material.name.title(),],
                    ],
                ],
                flex=True,
                col=True,
            )
        ],
    )
