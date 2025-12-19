from fastapi import Request
from htpy import Element, a, div, fragment, h1, h2, i, img, p

from pindb.database.pin import Pin
from pindb.templates.base import html_base
from pindb.templates.components.back_link import back_link
from pindb.templates.components.icon_list_element import icon_list_item
from pindb.utils import domain_from_url, format_currency_code


def pin_page(
    request: Request,
    pin: Pin,
) -> Element:
    return html_base(
        title=pin.name,
        body_content=fragment[
            div(
                class_="mx-auto px-10 my-5 gap-2 w-full grid grid-cols-1 min-md:gap-4 min-md:grid-cols-2 min-md:max-w-[160ch]"
            )[
                div(class_="min-md:col-span-2")[
                    back_link(),
                    h1[
                        pin.name,
                        a(
                            class_="font-semibold pl-4",
                            href=str(request.url_for("get_edit_pin", id=pin.id)),
                        )[
                            i(
                                data_lucide="pen",
                                class_="inline-block mb-1",
                            ),
                        ],
                    ],
                ],
                div(class_="w-full")[
                    img(
                        src=str(
                            request.url_for("get_image", guid=pin.front_image_guid)
                        ),
                        class_="w-full object-contain h-[60vh] bg-pin-base-500",
                    ),
                    pin.back_image_guid
                    and img(
                        src=str(request.url_for("get_image", guid=pin.back_image_guid)),
                        class_="w-full object-contain h-[60vh] bg-pin-base-500",
                    ),
                ],
                __pin_details(
                    request=request,
                    pin=pin,
                ),
            ]
        ],
    )


def __pin_details(request: Request, pin: Pin) -> Element:
    return div(class_="min-md:ml-2")[
        h2["Details"],
        __shops(pin=pin, request=request),
        __links(pin=pin),
        __acquisition(pin=pin),
        __original_price(pin=pin),
        __pin_sets(pin=pin, request=request),
        __tags(pin=pin, request=request),
        __materials(pin=pin, request=request),
        __description(pin=pin),
        __posts(pin=pin),
        __height(pin=pin),
        __width(pin=pin),
        __release_date(pin=pin),
        __end_date(pin=pin),
        __limited_edition(pin=pin),
        __number_produced(pin=pin),
        __funding(pin=pin),
    ]


def __shops(pin: Pin, request: Request) -> Element:
    return div(class_="flex flex-wrap gap-2 items-baseline")[
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
    ]


def __links(pin: Pin) -> Element | None:
    if not pin.links:
        return None
    return div(class_="flex flex-wrap gap-2 items-baseline")[
        p(class_="text-lg font-semibold")[
            i(data_lucide="link", class_="inline-block pr-2"),
            "Links",
        ],
        *[a(href=link.path)[domain_from_url(link.path)] for link in pin.links],
    ]


def __acquisition(pin: Pin) -> Element:
    return icon_list_item(
        icon="package",
        name="Acquisition Method",
        value=pin.acquisition_type.pretty_name(),
    )


def __original_price(pin: Pin) -> Element:
    return icon_list_item(
        icon="banknote",
        name="Original Price",
        value=format_currency_code(pin.original_price, pin.currency.code),
    )


def __pin_sets(pin: Pin, request: Request) -> Element | None:
    if not pin.sets:
        return None
    return div(class_="flex flex-wrap gap-2 items-baseline")[
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
    ]


def __tags(pin: Pin, request: Request) -> Element:
    return div(class_="flex flex-wrap gap-2 items-baseline")[
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
    ]


def __materials(pin: Pin, request: Request) -> Element:
    return div(class_="flex flex-wrap gap-2 items-baseline")[
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
    ]


def __description(pin: Pin) -> Element | None:
    if pin.description is None:
        return
    return div(class_="flex flex-wrap gap-2 items-baseline")[
        p(class_="text-lg font-semibold")["Description"],
        pin.description,
    ]


def __posts(pin: Pin) -> Element:
    return icon_list_item(
        icon="pin",
        name="Posts",
        value=str(pin.posts),
    )


def __height(pin: Pin) -> Element | None:
    if pin.height is None:
        return
    return icon_list_item(
        icon="move-vertical",
        name="Height",
        value=f"{pin.height:.2f}mm",
    )


def __width(pin: Pin) -> Element | None:
    if pin.width is None:
        return
    return icon_list_item(
        icon="move-horizontal",
        name="Width",
        value=f"{pin.width:.2f}mm",
    )


def __release_date(pin: Pin) -> Element | None:
    if pin.release_date is None:
        return
    return icon_list_item(
        icon="calendar-check-2",
        name="Released",
        value=str(pin.release_date),
    )


def __end_date(pin: Pin) -> Element | None:
    if pin.end_date is None:
        return
    return icon_list_item(
        icon="calendar-x-2",
        name="Ended",
        value=str(pin.end_date),
    )


def __limited_edition(pin: Pin) -> Element | None:
    if pin.limited_edition is None:
        return
    return icon_list_item(
        icon="sparkles",
        name="Limited Edition",
        value="Yes" if pin.limited_edition else "No",
    )


def __number_produced(pin: Pin) -> Element | None:
    if pin.number_produced is None:
        return
    return icon_list_item(
        icon="hash",
        name="Number Produced",
        value=str(pin.number_produced),
    )


def __funding(pin: Pin) -> Element | None:
    if pin.funding_type is None:
        return
    return icon_list_item(
        icon="hand-coins",
        name="Funding",
        value=pin.funding_type.title(),
    )
