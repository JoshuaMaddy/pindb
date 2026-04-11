from typing import Sequence

from fastapi import Request
from htpy import Element, fragment

from pindb.database.material import Material
from pindb.database.pin import Pin
from pindb.database.user import User
from pindb.templates.base import html_base
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.centered import centered_div
from pindb.templates.components.confirm_modal import confirm_modal
from pindb.templates.components.icon_button import icon_button
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
    user: User | None = getattr(getattr(request, "state", None), "user", None)
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
                            ("(P) " + material.name)
                            if material.is_pending
                            else material.name,
                        ]
                    ),
                    page_heading(
                        icon="anvil",
                        text=("(P) " + material.name.title())
                        if material.is_pending
                        else material.name.title(),
                        full_width=True,
                        extras=fragment[
                            user
                            and user.is_admin
                            and fragment[
                                icon_button(
                                    icon="pen",
                                    title="Edit material",
                                    href=str(
                                        request.url_for(
                                            "get_edit_material", id=material.id
                                        )
                                    ),
                                ),
                                confirm_modal(
                                    trigger=icon_button(
                                        icon="trash-2",
                                        title="Delete material",
                                        variant="danger",
                                    ),
                                    message=f'Delete the material "{material.name}"?',
                                    form_action=str(
                                        request.url_for(
                                            "post_delete_material", id=material.id
                                        )
                                    ),
                                ),
                            ],
                        ],
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
