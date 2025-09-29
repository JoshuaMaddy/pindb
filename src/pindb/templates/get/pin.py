from fastapi import Request
from htpy import a, br, div, fragment, h1, img, p

from pindb.database.pin import Pin
from pindb.templates.base import html_base


def pin_page(
    request: Request,
    pin: Pin,
):
    return html_base(
        body_content=fragment[
            div(class_="max-w-[80ch] mx-auto bg-blue-200 p-10")[
                h1(class_="text-xl font-bold")[pin.name],
                img(src=str(request.url_for("get_image", guid=pin.front_image_guid))),
                fragment[
                    pin.back_image_guid
                    and img(
                        src=str(request.url_for("get_image", guid=pin.back_image_guid))
                    )
                ],
                div[
                    p[f"Acquisition Method: {pin.acquisition_type.pretty_name()}"],
                    p[
                        f"Materials: {', '.join([material.name for material in pin.materials])}"
                    ],
                    p["Shops:"],
                    div[
                        *[
                            fragment[
                                a(href=str(request.url_for("get_shop", id=shop.id)))[
                                    shop.name
                                ],
                                br,
                            ]
                            for shop in pin.shops
                        ]
                    ],
                    p[f"Tags: {', '.join([tag.name for tag in pin.tags])}"],
                    fragment[
                        (pin.limited_edition is not None)
                        and p[f"Limited Edition: {pin.limited_edition}"]
                    ],
                    fragment[
                        (pin.number_produced is not None)
                        and p[f"Number Produced: {pin.number_produced}"]
                    ],
                    fragment[pin.release_date and p[f"Released: {pin.release_date}"]],
                    fragment[pin.end_date and p[f"Ended: {pin.end_date}"]],
                    fragment[
                        pin.funding_type and p[f"Funding Type: {pin.funding_type}"]
                    ],
                    fragment[pin.posts and p[f"Posts: {pin.posts}"]],
                    fragment[bool(pin.width) and p[f"Width: {pin.width}mm"]],
                    fragment[bool(pin.height) and p[f"Height: {pin.height}mm"]],
                    fragment[pin.description and p[f"Description: {pin.description}"]],
                ],
            ]
        ],
    )
