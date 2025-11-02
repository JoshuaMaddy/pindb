from fastapi import Request
from htpy import div, fragment, h1, i

from pindb.database.material import Material
from pindb.templates.base import html_base


def material_page(
    request: Request,
    material: Material,
):
    return html_base(
        body_content=fragment[
            div(class_="max-w-[80ch] mx-auto bg-blue-200 p-10 flex flex-col gap-2")[
                div(class_="flex w-full gap-2 items-baseline")[
                    i(data_lucide="anvil"),
                    h1[material.name.title(),],
                ]
            ]
        ],
    )
