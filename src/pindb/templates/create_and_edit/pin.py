from pathlib import Path
from typing import Sequence

from fastapi.datastructures import URL
from htpy import (
    Fragment,
    button,
    div,
    form,
    fragment,
    h1,
    h2,
    hr,
    input,
    label,
    option,
    select,
)

from pindb.database import Material, Shop, Tag
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
    shops: Sequence[Shop],
    tags: Sequence[Tag],
    pin_sets: Sequence[PinSet],
    pin: Pin | None = None,
):
    return html_base(
        body_content=centered_div(
            [
                h1["Create a Pin" if not pin else "Edit a Pin"],
                hr,
                form(
                    hx_post=str(post_url),
                    enctype="multipart/form-data",
                    class_="flex flex-col gap-2 [&_label]:font-semibold",
                )[
                    __required_fields(
                        materials=materials,
                        shops=shops,
                        tags=tags,
                        pin=pin,
                    ),
                    hr,
                    __optional_fields(pin=pin, pin_sets=pin_sets),
                    input(type="submit", value="Submit", class_="mt-2"),
                ],
            ]
        ),
        script_content=SCRIPT_CONTENT,
    )


def __required_fields(
    materials: Sequence[Material],
    shops: Sequence[Shop],
    tags: Sequence[Tag],
    pin: Pin | None = None,
) -> Fragment:
    return fragment[
        h2["Required"],
        label(for_="front_image")["Front Image"],
        input(
            type="file",
            id="image",
            name="front_image",
            accept="image/png, image/jpeg, image/jpg, image/webp",
            required=True if not pin else False,
        ),
        label(for_="name")["Name"],
        input(
            type="text",
            name="name",
            id="name",
            required=True,
            autocomplete="off",
            value=pin.name if pin else False,
        ),
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
        label(for_="original_price")["Original Price"],
        input(
            type="number",
            name="original_price",
            id="original_price",
            required=True,
            autocomplete="off",
            step="0.01",
            min="0",
            value=str(pin.original_price) if pin else False,
        ),
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


def __optional_fields(
    pin_sets: Sequence[PinSet],
    pin: Pin | None = None,
) -> Fragment:
    pin_links: None | list[Link] = None
    if pin:
        pin_links = list(pin.links)

    return fragment[
        h2["Optional"],
        # Images
        label(for_="back_image")["Back Image"],
        input(
            type="file",
            id="image",
            name="back_image",
            accept="image/png, image/jpeg, image/jpg, image/webp",
        ),
        # Pin Sets
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
        # Production
        label(for_="limited_edition")["Limited Edition"],
        input(
            name="limited_edition",
            id="limited_edition",
            type="checkbox",
            class_="self-start",
            checked=pin.limited_edition if pin and pin.limited_edition else None,
        ),
        label(for_="number_produced")["Number Produced"],
        input(
            name="number_produced",
            id="number_produced",
            type="number",
            min=0,
            step=1,
            value=pin.number_produced if pin and pin.number_produced else None,
        ),
        label(for_="release_date")["Release Date"],
        input(
            name="release_date",
            id="release_date",
            type="date",
            value=str(pin.release_date) if pin and pin.release_date else None,
        ),
        label(for_="end_date")["End Date"],
        input(
            name="end_date",
            id="end_date",
            type="date",
            value=str(pin.end_date) if pin and pin.end_date else None,
        ),
        label(for_="funding_type")["Funding Type"],
        select(
            name="funding_type",
            id="funding_type",
        )[
            [
                option(
                    value=funding_type,
                    selected=funding_type == pin.funding_type if pin else False,
                )[funding_type.replace("_", " ").title()]
                for funding_type in FundingType
            ]
        ],
        # Physical
        label(for_="posts")["Posts"],
        input(
            name="posts",
            id="posts",
            type="number",
            min=1,
            step=1,
            value=pin.posts if pin else 1,
        ),
        label(for_="width")["Width"],
        input(
            name="width",
            id="width",
            type="text",
            pattern=DIMENSION_PATTERN,
            value=f"{pin.width}mm" if pin and pin.width else False,
        ),
        label(for_="height")["Height"],
        input(
            name="height",
            id="height",
            type="text",
            pattern=DIMENSION_PATTERN,
            value=f"{pin.height}mm" if pin and pin.height else False,
        ),
        div[
            label(for_="links")["Links"],
            div(id="links", class_="grid grid-cols-[1fr_min-content] gap-2")[
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
        ],
    ]
