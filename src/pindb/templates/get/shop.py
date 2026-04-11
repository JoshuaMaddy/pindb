from typing import Sequence

from fastapi import Request
from htpy import Element, a, br, div, fragment, h2

from pindb.database import Shop, User
from pindb.database.pin import Pin
from pindb.templates.base import html_base
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.centered import centered_div
from pindb.templates.components.confirm_modal import confirm_modal
from pindb.templates.components.description_block import description_block
from pindb.templates.components.icon_button import icon_button
from pindb.templates.components.page_heading import page_heading
from pindb.templates.components.paginated_pin_grid import paginated_pin_grid


def shop_page(
    request: Request,
    shop: Shop,
    pins: Sequence[Pin],
    total_count: int,
    page: int,
    per_page: int,
) -> Element:
    user: User | None = getattr(getattr(request, "state", None), "user", None)
    return html_base(
        title=shop.name,
        request=request,
        body_content=centered_div(
            content=fragment[
                bread_crumb(
                    entries=[
                        (request.url_for("get_list_index"), "List"),
                        (request.url_for("get_list_shops"), "Shops"),
                        ("(P) " + shop.name) if shop.is_pending else shop.name,
                    ]
                ),
                page_heading(
                    icon="store",
                    text=("(P) " + shop.name) if shop.is_pending else shop.name,
                    full_width=True,
                    extras=fragment[
                        user
                        and user.is_admin
                        and fragment[
                            icon_button(
                                icon="pen",
                                title="Edit shop",
                                href=str(request.url_for("get_edit_shop", id=shop.id)),
                            ),
                            confirm_modal(
                                trigger=icon_button(
                                    icon="trash-2",
                                    title="Delete shop",
                                    variant="danger",
                                ),
                                message=f'Delete the shop "{shop.name}"?',
                                form_action=str(
                                    request.url_for("post_delete_shop", id=shop.id)
                                ),
                            ),
                        ],
                    ],
                ),
                description_block(shop.description),
                fragment[
                    bool(len(shop.links))
                    and div[
                        h2["Links"],
                        *[
                            fragment[a(href=link.path)[link.path], br]
                            for link in shop.links
                        ],
                    ]
                ],
                paginated_pin_grid(
                    request=request,
                    pins=pins,
                    total_count=total_count,
                    page=page,
                    page_url=str(request.url_for("get_shop", id=shop.id)),
                    per_page=per_page,
                ),
            ],
            flex=True,
            col=True,
        ),
    )
