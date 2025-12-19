from pathlib import Path
from typing import Sequence

from fastapi.datastructures import URL
from htpy import (
    Element,
    Fragment,
    VoidElement,
    button,
    div,
    form,
    fragment,
    h1,
    h2,
    hr,
    i,
    input,
    label,
    option,
    p,
    select,
    textarea,
)

from pindb.database import Material, Shop, Tag
from pindb.database.currency import Currency
from pindb.database.link import Link
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.models import AcquisitionType, FundingType
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div

DIMENSION_PATTERN = r".*?(\d*\.?\d*)\s*(([Ii]nch(?:es)?)|(in)|(IN)|([Cc]entimeters?)|(cm)|(CM)|([Mm]illimeters?)|(mm)|(MM))"

with open(
    Path(__file__).parent.parent / "js/pin_creation.js", "r", encoding="utf-8"
) as js_file:
    SCRIPT_CONTENT = js_file.read()


def pin_form(
    post_url: URL | str,
    materials: Sequence[Material],
    currencies: Sequence[Currency],
    shops: Sequence[Shop],
    tags: Sequence[Tag],
    pin_sets: Sequence[PinSet],
    pin: Pin | None = None,
) -> Element:
    return html_base(
        title="Create Pin" if not pin else "Edit Pin",
        body_content=centered_div(
            content=[
                h1["Create a Pin" if not pin else "Edit a Pin"],
                hr,
                form(
                    hx_post=str(post_url),
                    enctype="multipart/form-data",
                    class_="grid grid-cols-[1fr_2fr] max-sm:grid-cols-1 gap-2 [&_label]:font-semibold",
                    autocomplete="off",
                )[
                    div(class_="flex flex-col gap-2")[
                        __front_image_input(pin=pin),
                        __back_image_input(pin=pin),
                    ],
                    div(class_="grid grid-cols-[max-content_1fr] gap-2")[
                        __required_fields(
                            materials=materials,
                            shops=shops,
                            tags=tags,
                            pin=pin,
                            currencies=currencies,
                        ),
                        hr(class_="col-span-2"),
                        __optional_fields(pin=pin, pin_sets=pin_sets),
                        input(type="submit", value="Submit", class_="col-span-2 mt-2"),
                    ],
                ],
            ],
            wide=True,
        ),
        script_content=SCRIPT_CONTENT,
    )


def __required_fields(
    materials: Sequence[Material],
    shops: Sequence[Shop],
    tags: Sequence[Tag],
    currencies: Sequence[Currency],
    pin: Pin | None = None,
) -> Fragment:
    return fragment[
        h2(class_="col-span-2")["Required"],
        __name_input(pin=pin),
        __shops_input(pin=pin, shops=shops),
        __acquisition_input(pin=pin),
        __original_price_input(currencies=currencies, pin=pin),
        __material_ids_input(pin=pin, materials=materials),
        __tag_ids_input(pin=pin, tags=tags),
    ]


def __optional_fields(
    pin_sets: Sequence[PinSet],
    pin: Pin | None = None,
) -> Fragment:
    return fragment[
        h2(class_="col-span-2")["Optional"],
        # Images
        __pin_sets_ids_input(pin=pin, pin_sets=pin_sets),
        # Production
        __limited_edition_input(pin=pin),
        __number_produced_input(pin=pin),
        __release_date_input(pin=pin),
        __end_date_input(pin=pin),
        __funding_input(pin=pin),
        # Physical
        __posts_input(pin=pin),
        __width_input(pin=pin),
        __height_input(pin=pin),
        __links_input(pin=pin),
        __description_input(pin=pin),
    ]


def __front_image_input(pin: Pin | None) -> list[Element | VoidElement]:
    return [
        div(
            class_="image-drop w-full flex aspect-square justify-center items-center border-2 border-pin-border rounded-lg bg-cover bg-no-repeat bg-center transition-all duration-100 cursor-pointer hover:border-accent",
            data_input_id="front_image",
            id="front_image_preview",
            style=f"background-image: url(/get/image/{pin.front_image_guid})"
            if pin
            else False,
        )["Front Image" if not pin else ""],
        input(
            type="file",
            id="front_image",
            name="front_image",
            accept="image/png, image/jpeg, image/jpg, image/webp",
            required=True if not pin else False,
            class_="hidden",
            hidden=True,
        ),
    ]


def __back_image_input(pin: Pin | None) -> list[Element | VoidElement]:
    return [
        div(
            class_="image-drop w-full flex flex-col gap-1 aspect-square justify-center items-center border-2 border-pin-border rounded-lg bg-cover bg-no-repeat bg-center transition-all duration-100 cursor-pointer hover:border-accent",
            data_input_id="back_image",
            id="back_image_preview",
            style=f"background-image: url(/get/image/{pin.back_image_guid})"
            if pin
            else False,
        )[
            fragment[
                p["Back Image"],
                i["(Optional)"],
            ]
            if (pin and not pin.back_image_guid) or not pin
            else ""
        ],
        input(
            type="file",
            id="back_image",
            name="back_image",
            accept="image/png, image/jpeg, image/jpg, image/webp",
            class_="hidden",
            hidden=True,
        ),
    ]


def __name_input(pin: Pin | None) -> list[Element | VoidElement]:
    return [
        label(for_="name")["Name"],
        input(
            name="name",
            id="name",
            type="text",
            value=pin.name if pin else "",
        ),
    ]


def __shops_input(
    shops: Sequence[Shop],
    pin: Pin | None,
) -> list[Element | VoidElement]:
    return [
        label(for_="shop_ids")["Shops"],
        select(
            name="shop_ids",
            id="shop_ids",
            required=True,
            multiple=True,
            class_="multi-select",
        )[
            [
                option(
                    value=shop.id,
                    selected=shop in pin.shops if pin else False,
                )[shop.name]
                for shop in shops
            ]
        ],
    ]


def __acquisition_input(pin: Pin | None) -> list[Element | VoidElement]:
    return [
        label(for_="acquisition_type")["Acquisition"],
        select(
            name="acquisition_type",
            id="acquisition_type",
            class_="single-select",
            required=True,
        )[
            [
                option(
                    value=acquisition_type,
                    selected=acquisition_type == pin.acquisition_type if pin else False,
                )[acquisition_type.replace("_", " ").title()]
                for acquisition_type in AcquisitionType
            ]
        ],
    ]


def __original_price_input(
    currencies: Sequence[Currency],
    pin: Pin | None,
) -> list[Element | VoidElement]:
    return [
        label(for_="original_price")["Original Price"],
        div(class_="flex w-full gap-1")[
            input(
                type="number",
                name="original_price",
                id="original_price",
                required=True,
                autocomplete="off",
                step="0.01",
                min="0",
                value=str(pin.original_price) if pin else False,
                class_="grow",
            ),
            select(
                name="currency_id",
                id="currency_id",
            )[
                [
                    option(
                        value=currency.id,
                        selected=currency.id == pin.currency_id
                        if pin
                        else currency.id == 840,
                    )[currency.code]
                    for currency in currencies
                ]
            ],
        ],
    ]


def __material_ids_input(
    pin: Pin | None,
    materials: Sequence[Material],
) -> list[Element | VoidElement]:
    return [
        label(for_="material_ids")["Materials"],
        select(
            name="material_ids",
            id="material_ids",
            required=True,
            multiple=True,
            class_="multi-select",
        )[
            [
                option(
                    value=material.id,
                    selected=material in pin.materials if pin else False,
                )[material.name]
                for material in materials
            ]
        ],
    ]


def __tag_ids_input(
    pin: Pin | None,
    tags: Sequence[Tag],
) -> list[Element | VoidElement]:
    return [
        label(for_="tag_ids")["Tags"],
        select(
            name="tag_ids",
            id="tag_ids",
            required=True,
            multiple=True,
            class_="multi-select",
        )[
            [
                option(
                    value=tag.id,
                    selected=tag in pin.tags if pin else False,
                )[tag.name]
                for tag in tags
            ]
        ],
    ]


def __pin_sets_ids_input(
    pin: Pin | None,
    pin_sets: Sequence[PinSet],
) -> list[Element | VoidElement]:
    return [
        label(for_="pin_sets_ids")["Pin Sets"],
        select(
            name="pin_sets_ids",
            id="pin_sets_ids",
            multiple=True,
            class_="multi-select",
        )[
            [
                option(
                    value=pin_set.id,
                    selected=pin_set in pin.sets if pin else False,
                )[pin_set.name]
                for pin_set in pin_sets
            ]
        ],
    ]


def __limited_edition_input(pin: Pin | None) -> list[Element | VoidElement]:
    selected_classes = "bg-pin-main border-accent text-accent grow"
    return [
        label(for_="limited_edition")["Limited Edition"],
        input(
            name="limited_edition",
            id="limited_edition",
            type="checkbox",
            class_="self-start",
            hidden=True,
            checked=pin.limited_edition if pin and pin.limited_edition else None,
        ),
        div(class_="flex gap-2 w-full")[
            button(
                id="limited_edition_yes",
                class_=selected_classes if pin and pin.limited_edition else "grow",
                type="button",
            )["Yes"],
            button(
                id="limited_edition_no",
                class_="grow" if pin and pin.limited_edition else selected_classes,
                type="button",
            )["No"],
        ],
    ]


def __number_produced_input(pin: Pin | None) -> list[Element | VoidElement]:
    return [
        label(for_="number_produced")["Number Produced"],
        input(
            name="number_produced",
            id="number_produced",
            type="number",
            min=0,
            step=1,
            value=pin.number_produced if pin and pin.number_produced else None,
        ),
    ]


def __release_date_input(pin: Pin | None) -> list[Element | VoidElement]:
    return [
        label(for_="release_date")["Release Date"],
        input(
            name="release_date",
            id="release_date",
            type="date",
            value=str(pin.release_date) if pin and pin.release_date else None,
        ),
    ]


def __end_date_input(pin: Pin | None) -> list[Element | VoidElement]:
    return [
        label(for_="end_date")["End Date"],
        input(
            name="end_date",
            id="end_date",
            type="date",
            value=str(pin.end_date) if pin and pin.end_date else None,
        ),
    ]


def __funding_input(pin: Pin | None) -> list[Element | VoidElement]:
    return [
        label(for_="funding_type")["Funding Type"],
        select(
            name="funding_type",
            id="funding_type",
            class_="single-select",
        )[
            [
                option(
                    value=funding_type,
                    selected=funding_type == pin.funding_type if pin else False,
                )[funding_type.replace("_", " ").title()]
                for funding_type in FundingType
            ]
        ],
    ]


def __posts_input(pin: Pin | None) -> list[Element | VoidElement]:
    return [
        label(for_="posts")["Posts"],
        input(
            name="posts",
            id="posts",
            type="number",
            min=1,
            step=1,
            value=pin.posts if pin else 1,
        ),
    ]


def __width_input(pin: Pin | None) -> list[Element | VoidElement]:
    return [
        label(for_="width")["Width"],
        input(
            name="width",
            id="width",
            type="text",
            pattern=DIMENSION_PATTERN,
            value=f"{pin.width}mm" if pin and pin.width else False,
        ),
    ]


def __height_input(pin: Pin | None) -> list[Element | VoidElement]:
    return [
        label(for_="height")["Height"],
        input(
            name="height",
            id="height",
            type="text",
            pattern=DIMENSION_PATTERN,
            value=f"{pin.height}mm" if pin and pin.height else False,
        ),
    ]


def __links_input(pin: Pin | None) -> Element:
    pin_links: None | list[Link] = None
    if pin:
        pin_links = list(pin.links)

    return div(class_="col-span-2")[
        label(for_="links")["Links"],
        div(id="links", class_="grid grid-cols-[1fr_min-content] gap-2 mt-2")[
            input(
                name="links",
                id="link_0",
                type="text",
                class_="col-span-2",
                value=pin_links.pop(0).path if pin_links else None,
            ),
            (pin_links is not None and len(pin_links) != 0)
            and [
                fragment[
                    input(
                        name="links",
                        id=f"link_{i}",
                        type="text",
                        value=link.path,
                    ),
                    button(class_="remove-link-button")["Remove"],
                ]
                for i, link in enumerate(pin_links)
            ],
        ],
        button(
            id="add-link-button",
            class_="w-full mt-2",
            type="button",
        )["Add Link"],
    ]


def __description_input(pin: Pin | None) -> list[Element | VoidElement]:
    return [
        label(for_="description", class_="col-span-2")["Description"],
        textarea(
            name="description",
            id="description",
            type="text",
            class_="col-span-2",
            value=pin.description if pin else "",
        ),
    ]
