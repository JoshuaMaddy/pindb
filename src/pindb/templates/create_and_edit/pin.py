import json
from pathlib import Path
from typing import Sequence

from fastapi import Request
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
from markupsafe import Markup

from pindb.database import Artist, Material, Shop, Tag
from pindb.database.currency import Currency
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.models import AcquisitionType, FundingType
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div

DIMENSION_PATTERN = r".*?(\d*\.?\d*)\s*(([Ii]nch(?:es)?)|(in)|(IN)|([Cc]entimeters?)|(cm)|(CM)|([Mm]illimeters?)|(mm)|(MM))"

with open(
    file=Path(__file__).parent.parent / "js/pin_creation.js",
    mode="r",
    encoding="utf-8",
) as js_file:
    SCRIPT_CONTENT: str = js_file.read()


def pin_form(
    post_url: URL | str,
    materials: Sequence[Material],
    currencies: Sequence[Currency],
    shops: Sequence[Shop],
    tags: Sequence[Tag],
    pin_sets: Sequence[PinSet],
    artists: Sequence[Artist],
    request: Request,
    pin: Pin | None = None,
) -> Element:
    return html_base(
        title="Create Pin" if not pin else "Edit Pin",
        body_content=centered_div(
            content=[
                h1["Create a Pin" if not pin else "Edit a Pin"],
                _pending_notice(request=request, pin=pin),
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
                            artists=artists,
                            pin=pin,
                            currencies=currencies,
                        ),
                        hr(class_="col-span-2"),
                        __optional_fields(pin=pin, pin_sets=pin_sets),
                        input(type="submit", value="Submit", class_="col-span-2 mt-2"),
                    ],
                ],
            ],
        ),
        script_content=SCRIPT_CONTENT,
        request=request,
    )


def _pending_notice(request: Request, pin: Pin | None) -> Element | str:
    user = getattr(getattr(request, "state", None), "user", None)
    if user is None or user.is_admin:
        return ""
    if not (user.is_editor or user.is_admin):
        return ""
    if pin and not pin.is_pending:
        return ""
    msg = (
        "This entry is pending admin approval."
        if pin and pin.is_pending
        else "Your submission will be reviewed by an admin before becoming visible."
    )
    return div(
        class_="rounded bg-amber-900 border border-amber-600 text-amber-200 px-4 py-2 text-sm my-2"
    )[
        i(data_lucide="clock", class_="inline-block w-4 h-4 mr-1"),
        msg,
    ]


def __required_fields(
    materials: Sequence[Material],
    shops: Sequence[Shop],
    tags: Sequence[Tag],
    artists: Sequence[Artist],
    currencies: Sequence[Currency],
    pin: Pin | None = None,
) -> Fragment:
    return fragment[
        h2(class_="col-span-2")["Required"],
        __name_input(pin=pin),
        __shops_input(pin=pin, shops=shops),
        __acquisition_input(pin=pin),
        __grades_input(currencies=currencies, pin=pin),
        __material_ids_input(pin=pin, materials=materials),
        __tag_ids_input(pin=pin, tags=tags),
        __artist_ids_input(pin=pin, artists=artists),
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
                )["(P) " + shop.name if shop.is_pending else shop.name]
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


def __grades_input(
    currencies: Sequence[Currency],
    pin: Pin | None,
) -> list[Element | VoidElement | Markup]:
    # Prepare initial grades data
    grades_data: list[dict[str, str]] = []
    if pin and pin.grades:
        grades_data = [
            {"name": str(grade.name), "price": str(grade.price)} for grade in pin.grades
        ]

    # Ensure at least one empty grade
    if not grades_data:
        grades_data = [{"name": "", "price": ""}]

    # Default currency
    default_currency_id = pin.currency_id if pin else 840

    grades_json = json.dumps(grades_data)

    return [
        label(for_="grade")["Grade"],
        Markup(f"""<div class="flex w-full gap-2">
            <div class="flex flex-col gap-2 grow" x-data="{{ grades: {grades_json.replace('"', "'")} }}">
                <template x-for="(grade, index) in grades" :key="index">
                    <div class="gap-2 flex">
                        <input class="grow" type="text" name="grade_names" x-model="grades[index].name" required autocomplete="off" placeholder="Grade">
                        <input class="w-25" type="number" name="grade_prices" x-model="grades[index].price" required autocomplete="off" step="0.01" min="0" placeholder="Price">
                        <button type="button" @click="grades.splice(index, 1)" x-show="grades.length > 1" class="remove-grade-button">Remove</button>
                    </div>
                </template>
                <button type="button" @click="grades.push({{name: '', price: ''}})" class="w-full">Add Grade</button>
            </div>
        """),
        select(
            name="currency_id",
            id="currency_id",
        )[
            [
                option(
                    value=currency.id,
                    selected=currency.id == default_currency_id,
                )[currency.code]
                for currency in currencies
            ]
        ],
        Markup("</div>"),
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
                )["(P) " + material.name if material.is_pending else material.name]
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
                )["(P) " + tag.name if tag.is_pending else tag.name]
                for tag in tags
            ]
        ],
    ]


def __artist_ids_input(
    pin: Pin | None,
    artists: Sequence[Artist],
) -> list[Element | VoidElement]:
    return [
        label(for_="artist_ids")["Artists"],
        select(
            name="artist_ids",
            id="artist_ids",
            multiple=True,
            class_="multi-select",
        )[
            [
                option(
                    value=artist.id,
                    selected=artist in pin.artists if pin else False,
                )["(P) " + artist.name if artist.is_pending else artist.name]
                for artist in artists
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
                )["(P) " + pin_set.name if pin_set.is_pending else pin_set.name]
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


def __links_input(pin: Pin | None) -> Element | Markup:
    pin_links: list[str] = []
    if pin and pin.links:
        pin_links = [link.path for link in pin.links]

    # Ensure at least one empty field
    if not pin_links:
        pin_links = [""]

    links_json = json.dumps(pin_links)

    return div(class_="col-span-2")[
        label(for_="links")["Links"],
        Markup(f"""<div class="mt-2" x-data="{{ links: {links_json.replace('"', "'")} }}">
            <template x-for="(link, index) in links" :key="index">
                <div class="grid grid-cols-[1fr_min-content] gap-2 mb-2">
                    <input 
                        type="text"
                        name="links"
                        x-model="links[index]"
                        class="col-span-1">
                    <button 
                        type="button" 
                        @click="links.splice(index, 1)" 
                        x-show="links.length > 1"
                        class="remove-link-button">Remove</button>
                </div>
            </template>
            <button 
                type="button" 
                @click="links.push('')" 
                class="w-full mt-2">Add Link</button>
        </div>"""),
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
