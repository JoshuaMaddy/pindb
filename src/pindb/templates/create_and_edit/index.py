"""
htpy page and fragment builders: `templates/create_and_edit/index.py`.
"""

from fastapi import Request
from htpy import Element, div, h1, hr, i

from pindb.templates.base import html_base
from pindb.templates.components.layout.card import card
from pindb.templates.components.layout.centered import centered_div


def create_index(request: Request) -> Element:
    user = getattr(request.state, "user", None)
    show_bulk_pin_import = user is not None and user.is_admin

    return html_base(
        title="Create",
        request=request,
        body_content=centered_div(
            content=[
                div(class_="md:col-span-2")[
                    h1["Create"],
                    hr,
                ],
                card(
                    href=request.url_for("get_create_pin"),
                    content="Pin",
                    icon="circle-star",
                ),
                card(
                    href=request.url_for("get_create_shop"),
                    content="Shop",
                    icon="store",
                ),
                card(
                    href=request.url_for("get_create_tag"),
                    content="Tag",
                    icon="tag",
                ),
                card(
                    href=request.url_for("get_create_pin_set"),
                    content="Pin Set",
                    icon="layout-grid",
                ),
                card(
                    href=request.url_for("get_create_artist"),
                    content="Artist",
                    icon="palette",
                ),
                div(class_="md:col-span-2")[hr],
                *(
                    [
                        div(class_="md:col-span-2")[
                            card(
                                href=request.url_for("get_bulk_pin"),
                                content="Bulk Import Pins",
                                icon="table-2",
                                additional_classes="max-md:hidden",
                            ),
                            div(
                                class_="md:hidden flex gap-2 rounded-xl border border-lightest bg-main p-2 text-base-text opacity-80"
                            )[
                                i(
                                    data_lucide="table-2",
                                    class_="inline-block shrink-0",
                                ),
                                div(class_="flex min-w-0 flex-col gap-0.5")[
                                    div(class_="font-semibold")["Bulk Import Pins"],
                                    div(class_="text-sm text-base-text")[
                                        "Not available on small screens."
                                    ],
                                ],
                            ],
                        ],
                    ]
                    if show_bulk_pin_import
                    else []
                ),
                div(class_="md:col-span-2")[
                    card(
                        href=request.url_for("get_bulk_tag"),
                        content="Bulk Create Tags",
                        icon="tags",
                        additional_classes="max-md:hidden",
                    ),
                    div(
                        class_="md:hidden flex gap-2 rounded-xl border border-lightest bg-main p-2 text-base-text opacity-80"
                    )[
                        i(data_lucide="tags", class_="inline-block shrink-0"),
                        div(class_="flex min-w-0 flex-col gap-0.5")[
                            div(class_="font-semibold")["Bulk Create Tags"],
                            div(class_="text-sm text-base-text")[
                                "Not available on small screens."
                            ],
                        ],
                    ],
                ],
            ],
            additional_classes="grid min-md:grid-cols-2",
            content_width="small",
        ),
    )
