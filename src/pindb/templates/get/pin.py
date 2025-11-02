from fastapi import Request
from htpy import Element, a, div, fragment, h1, h2, i, img, p

from pindb.database.pin import Pin
from pindb.templates.base import html_base
from pindb.templates.components.icon_list_element import icon_list_item


def pin_page(
    request: Request,
    pin: Pin,
):
    return html_base(
        body_content=fragment[
            div(class_="max-w-[80ch] mx-auto p-10 flex flex-col gap-2")[
                h1[pin.name],
                img(src=str(request.url_for("get_image", guid=pin.front_image_guid))),
                fragment[
                    pin.back_image_guid
                    and img(
                        src=str(request.url_for("get_image", guid=pin.back_image_guid))
                    )
                ],
                __pin_details(
                    request=request,
                    pin=pin,
                ),
            ]
        ],
    )


def __pin_details(request: Request, pin: Pin) -> Element:
    return div[
        h2["Details"],
        # package
        icon_list_item(
            icon="package",
            name="Acquisition Method",
            value=pin.acquisition_type.pretty_name(),
        ),
        div(class_="flex flex-wrap gap-2 items-baseline")[
            p(class_="text-lg font-semibold")[
                i(data_lucide="store", class_="inline-block pr-2"),
                "Shops",
            ],
            *[
                a(
                    href=str(
                        request.url_for(
                            "get_shop",
                            id=shop.id,
                        )
                    )
                )[shop.name]
                for shop in pin.shops
            ],
        ],
        div(class_="flex flex-wrap gap-2 items-baseline")[
            p(class_="text-lg font-semibold")[
                i(data_lucide="tag", class_="inline-block pr-2"),
                "Tags",
            ],
            *[
                a(
                    href=str(
                        request.url_for(
                            "get_tag",
                            id=tag.id,
                        )
                    )
                )[tag.name]
                for tag in pin.tags
            ],
        ],
        div(class_="flex flex-wrap gap-2 items-baseline")[
            p(class_="text-lg font-semibold")[
                i(data_lucide="layout-grid", class_="inline-block pr-2"),
                "Pin Sets",
            ],
            *[
                a(
                    href=str(
                        request.url_for(
                            "get_pin_set",
                            id=pin_set.id,
                        )
                    )
                )[pin_set.name.title()]
                for pin_set in pin.sets
            ],
        ],
        div(class_="flex flex-wrap gap-2 items-baseline")[
            p(class_="text-lg font-semibold")[
                i(data_lucide="anvil", class_="inline-block pr-2"),
                "Materials",
            ],
            *[
                a(
                    href=str(
                        request.url_for(
                            "get_material",
                            id=material.id,
                        )
                    )
                )[material.name.title()]
                for material in pin.materials
            ],
        ],
        pin.description
        and div(class_="flex flex-wrap gap-2 items-baseline")[
            p(class_="text-lg font-semibold")["Description"],
            pin.description,
        ],
        pin.posts
        and icon_list_item(
            icon="pin",
            name="Posts",
            value=str(pin.posts),
        ),
        bool(pin.height)
        and icon_list_item(
            icon="move-vertical",
            name="Height",
            value=f"{pin.height:.2f}mm",
        ),
        bool(pin.width)
        and icon_list_item(
            icon="move-horizontal",
            name="Width",
            value=f"{pin.width:.2f}mm",
        ),
        pin.release_date
        and icon_list_item(
            icon="calendar-check-2",
            name="Released",
            value=str(pin.release_date),
        ),
        pin.end_date
        and icon_list_item(
            icon="calendar-x-2",
            name="Ended",
            value=str(pin.end_date),
        ),
        pin.limited_edition
        and icon_list_item(
            icon="sparkles",
            name="Limited Edition",
            value="Yes" if pin.limited_edition else "No",
        ),
        (pin.number_produced is not None)
        and icon_list_item(
            icon="hash",
            name="Number Produced",
            value=str(pin.number_produced),
        ),
        pin.funding_type
        and icon_list_item(
            icon="hand-coins",
            name="Funding",
            value=pin.funding_type.title(),
        ),
    ]
