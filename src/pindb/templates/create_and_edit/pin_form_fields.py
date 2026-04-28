"""
Field builders for the pin create/edit form.
"""

import json
import uuid
from typing import Sequence

from fastapi import Request
from htpy import (
    Element,
    Fragment,
    VoidElement,
    button,
    div,
    fragment,
    h2,
    i,
    input,
    label,
    option,
    p,
    select,
    span,
)
from markupsafe import Markup
from titlecase import titlecase

from pindb.database import Artist, Shop, Tag
from pindb.database.currency import Currency
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.model_utils import MAGNITUDE_INPUT_PATTERN
from pindb.models import AcquisitionType, FundingType
from pindb.templates.components.forms.markdown_editor import markdown_editor
from pindb.templates.components.forms.name_availability import (
    name_availability_field,
    name_check_attrs,
)


def _required_fields(
    *,
    shops: Sequence[Shop],
    tags: Sequence[Tag],
    currencies: Sequence[Currency],
    request: Request,
    pin: Pin | None = None,
    name_check_exclude_id: int | None = None,
) -> Fragment:
    return fragment[
        h2(class_="col-span-full")["Required"],
        _name_input(
            pin=pin,
            request=request,
            exclude_id=name_check_exclude_id,
        ),
        _shops_input(pin=pin, shops=shops),
        _acquisition_input(pin=pin),
        _grades_input(currencies=currencies, pin=pin),
        _tag_ids_input(pin=pin, tags=tags, request=request),
    ]


def _optional_fields(
    *,
    artists: Sequence[Artist],
    pin_sets: Sequence[PinSet],
    variant_pins: Sequence[Pin],
    unauthorized_copy_pins: Sequence[Pin],
    pin: Pin | None = None,
) -> Fragment:
    return fragment[
        h2(class_="col-span-full")["Optional"],
        _artist_ids_input(pin=pin, artists=artists),
        _pin_sets_ids_input(pin=pin, pin_sets=pin_sets),
        _variant_pins_input(pin=pin, variant_pins=variant_pins),
        _unauthorized_copy_pins_input(
            pin=pin, unauthorized_copy_pins=unauthorized_copy_pins
        ),
        _limited_edition_input(pin=pin),
        _number_produced_input(pin=pin),
        _release_date_input(pin=pin),
        _end_date_input(pin=pin),
        _funding_input(pin=pin),
        _posts_input(pin=pin),
        _width_input(pin=pin),
        _height_input(pin=pin),
        _links_input(pin=pin),
        _description_input(pin=pin),
    ]


def _front_image_input(*, pin: Pin | None) -> list[Element | VoidElement]:
    return [
        div(
            class_="image-drop w-full flex aspect-square justify-center items-center border-2 border-lightest rounded-lg bg-cover bg-no-repeat bg-center transition-all duration-100 cursor-pointer hover:border-accent",
            data_input_id="front_image",
            id="front_image_preview",
            data_pin_field="front",
            style=f"background-image: url(/get/image/{pin.front_image_guid})"
            if pin
            else False,
        )[
            fragment["Front Image", span(class_="text-error-main ml-0.5")["*"]]
            if not pin
            else ""
        ],
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


def _back_image_input(*, pin: Pin | None) -> list[Element | VoidElement]:
    return [
        div(
            class_="image-drop w-full flex flex-col gap-1 aspect-square justify-center items-center border-2 border-lightest rounded-lg bg-cover bg-no-repeat bg-center transition-all duration-100 cursor-pointer hover:border-accent",
            data_input_id="back_image",
            id="back_image_preview",
            style=f"background-image: url(/get/image/{pin.back_image_guid})"
            if pin and pin.back_image_guid
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


def _text_field(
    *,
    name: str,
    label_text: str,
    value: str | int | float | None,
    required: bool = False,
    input_type: str = "text",
    placeholder: str | None = None,
    pattern: str | None = None,
    min_value: int | None = None,
    step: int | str | None = None,
) -> list[Element | VoidElement]:
    """Reusable label + input pair for the pin form grid."""
    label_element = (
        label(for_=name)[label_text, span(class_="text-error-main ml-0.5")["*"]]
        if required
        else label(for_=name)[label_text]
    )
    normalized_value: str | int | None = (
        str(value) if isinstance(value, float) else value
    )
    return [
        label_element,
        input(
            name=name,
            id=name,
            type=input_type,
            required=required or None,
            autocomplete="off",
            value=normalized_value if normalized_value is not None else False,
            placeholder=placeholder or False,
            pattern=pattern or False,
            min=min_value,
            step=step,
            class_="w-full min-w-0",
        ),
    ]


def _name_input(
    *,
    pin: Pin | None,
    request: Request,
    exclude_id: int | None,
) -> list[Element | VoidElement]:
    name_feedback_id: str = "pin-name-availability-feedback"
    return [
        label(for_="name")["Name", span(class_="text-error-main ml-0.5")["*"]],
        name_availability_field(
            feedback_id=name_feedback_id,
            data_pin_field="name",
            child=input(
                name="name",
                id="name",
                type="text",
                required=True,
                autocomplete="off",
                value=pin.name if pin else "",
                placeholder="e.g. Cherry Blossom Artist Edition",
                class_="w-full min-w-0",
                **name_check_attrs(
                    check_url=str(request.url_for("get_create_check_name")),
                    kind="pin",
                    target_id=name_feedback_id,
                    exclude_id=exclude_id,
                ),
            ),
        ),
    ]


def _shops_input(
    *,
    shops: Sequence[Shop],
    pin: Pin | None,
) -> list[Element | VoidElement]:
    return [
        label(for_="shop_ids")["Shops", span(class_="text-error-main ml-0.5")["*"]],
        select(
            name="shop_ids",
            id="shop_ids",
            required=True,
            multiple=True,
            class_="multi-select w-full min-w-0",
            data_entity_type="shop",
            data_pin_field="shops",
        )[
            [
                option(
                    value=str(shop.id),
                    selected=shop in pin.shops if pin else False,
                )["(P) " + shop.name if shop.is_pending else shop.name]
                for shop in shops
            ]
        ],
    ]


def _acquisition_input(*, pin: Pin | None) -> list[Element | VoidElement]:
    return [
        label(for_="acquisition_type")[
            "Acquisition", span(class_="text-error-main ml-0.5")["*"]
        ],
        select(
            name="acquisition_type",
            id="acquisition_type",
            class_="single-select w-full min-w-0",
            required=True,
            data_pin_field="acquisition",
        )[
            [
                option(
                    value=acquisition_type,
                    selected=acquisition_type == pin.acquisition_type if pin else False,
                )[titlecase(acquisition_type.replace("_", " "))]
                for acquisition_type in AcquisitionType
            ]
        ],
    ]


def _grades_input(
    *,
    currencies: Sequence[Currency],
    pin: Pin | None,
) -> list[Element | VoidElement | Markup]:
    grades_data: list[dict[str, str]] = []
    if pin and pin.grades:
        grades_data = [
            {
                "id": str(uuid.uuid4()),
                "name": str(grade.name),
                "price": "" if grade.price is None else str(grade.price),
            }
            for grade in pin.grades
        ]

    if not grades_data:
        grades_data = [{"id": str(uuid.uuid4()), "name": "Normal", "price": ""}]

    default_currency_id = pin.currency_id if pin else 999
    grades_json = json.dumps(grades_data)

    return [
        label(for_="grade")["Grade", span(class_="text-error-main ml-0.5")["*"]],
        Markup(f"""<div class="flex w-full min-w-0 flex-wrap gap-2">
            <div id="pin-grade-section" data-pin-field="grades" class="flex min-w-0 flex-1 flex-col gap-2" x-data="{{ grades: {grades_json.replace('"', "'")} }}">
                <template x-for="grade in grades" :key="grade.id">
                    <div class="flex min-w-0 flex-col gap-2 sm:flex-row sm:flex-nowrap sm:items-center">
                        <input class="w-full min-w-0 sm:w-auto sm:min-w-0 sm:flex-1" type="text" name="grade_names" x-model="grade.name" required autocomplete="off" placeholder="Grade">
                        <input class="w-full min-w-0 sm:w-25" type="number" name="grade_prices" x-model="grade.price" autocomplete="off" step="0.01" min="0" placeholder="Unknown">
                        <button type="button" @click="grades.splice(grades.indexOf(grade), 1)" x-show="grades.length > 1" class="remove-grade-button w-full sm:w-auto sm:shrink-0">Remove</button>
                    </div>
                </template>
                <button type="button" @click="grades.push({{ id: crypto.randomUUID(), name: '', price: '' }})" class="w-full">Add Grade</button>
            </div>
        """),
        select(
            name="currency_id",
            id="currency_id",
            class_="w-full min-w-0 sm:w-auto sm:min-w-32",
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


def _tag_ids_input(
    *,
    pin: Pin | None,
    tags: Sequence[Tag],
    request: Request,
) -> list[Element | VoidElement]:
    preview_url = str(request.url_for("get_tag_implication_preview"))
    return [
        label(for_="tag_ids")["Tags", span(class_="text-error-main ml-0.5")["*"]],
        select(
            name="tag_ids",
            id="tag_ids",
            required=True,
            multiple=True,
            class_="multi-select w-full min-w-0",
            data_entity_type="tag",
            data_pin_field="tags",
            hx_get=preview_url,
            hx_swap="innerHTML",
            hx_trigger="load, change",
            hx_include="[name='tag_ids']",
            hx_target="#implication-preview",
        )[
            [
                option(
                    value=str(tag.id),
                    selected=tag in pin.tags if pin else False,
                    data_category=tag.category.value,
                )["(P) " + tag.display_name if tag.is_pending else tag.display_name]
                for tag in sorted(tags, key=lambda tag: (tag.category, tag.name))
            ]
        ],
        div(id="implication-preview", class_="col-span-full"),
    ]


def _artist_ids_input(
    *,
    pin: Pin | None,
    artists: Sequence[Artist],
) -> list[Element | VoidElement]:
    return [
        label(for_="artist_ids")["Artists"],
        select(
            name="artist_ids",
            id="artist_ids",
            multiple=True,
            class_="multi-select w-full min-w-0",
            data_entity_type="artist",
        )[
            [
                option(
                    value=str(artist.id),
                    selected=artist in pin.artists if pin else False,
                )["(P) " + artist.name if artist.is_pending else artist.name]
                for artist in artists
            ]
        ],
    ]


def _pin_sets_ids_input(
    *,
    pin: Pin | None,
    pin_sets: Sequence[PinSet],
) -> list[Element | VoidElement]:
    return [
        label(for_="pin_sets_ids")["Pin Sets"],
        select(
            name="pin_sets_ids",
            id="pin_sets_ids",
            multiple=True,
            class_="multi-select w-full min-w-0",
            data_entity_type="pin_set",
        )[
            [
                option(
                    value=str(pin_set.id),
                    selected=pin_set in pin.sets if pin else False,
                )["(P) " + pin_set.name if pin_set.is_pending else pin_set.name]
                for pin_set in pin_sets
            ]
        ],
    ]


def _pin_option(*, pin_obj: Pin) -> Element:
    return option(
        value=str(pin_obj.id),
        selected=True,
        data_thumbnail=f"/get/image/{pin_obj.front_image_guid}?w=100",
    )["(P) " + pin_obj.name if pin_obj.is_pending else pin_obj.name]


def _variant_pins_input(
    *,
    pin: Pin | None,
    variant_pins: Sequence[Pin],
) -> list[Element | VoidElement]:
    return [
        label(for_="variant_pin_ids")["Variants"],
        select(
            name="variant_pin_ids",
            id="variant_pin_ids",
            multiple=True,
            class_="multi-select w-full min-w-0",
            data_entity_type="pin",
        )[[_pin_option(pin_obj=variant) for variant in variant_pins]],
    ]


def _unauthorized_copy_pins_input(
    *,
    pin: Pin | None,
    unauthorized_copy_pins: Sequence[Pin],
) -> list[Element | VoidElement]:
    return [
        label(for_="unauthorized_copy_pin_ids")["Unauthorized Copies"],
        select(
            name="unauthorized_copy_pin_ids",
            id="unauthorized_copy_pin_ids",
            multiple=True,
            class_="multi-select w-full min-w-0",
            data_entity_type="pin",
        )[[_pin_option(pin_obj=copy_pin) for copy_pin in unauthorized_copy_pins]],
    ]


def _limited_edition_input(*, pin: Pin | None) -> list[Element | VoidElement]:
    selected_classes = "bg-main border-accent text-accent grow"
    yes_selected = pin is not None and pin.limited_edition is True
    no_selected = pin is not None and pin.limited_edition is False
    limited_edition_input_kwargs: dict[str, object] = {
        "name": "limited_edition",
        "id": "limited_edition",
        "type": "checkbox",
        "class_": "self-start",
        "hidden": True,
    }
    if pin is not None and pin.limited_edition is not None:
        limited_edition_input_kwargs["checked"] = True
        limited_edition_input_kwargs["value"] = (
            "true" if pin.limited_edition else "false"
        )

    return [
        label(for_="limited_edition")["Limited Edition"],
        div(class_="flex w-full min-w-0 flex-col gap-2")[
            input(**limited_edition_input_kwargs),
            div(class_="flex w-full min-w-0 gap-2")[
                button(
                    id="limited_edition_yes",
                    class_=selected_classes if yes_selected else "grow",
                    type="button",
                )["Yes"],
                button(
                    id="limited_edition_no",
                    class_=selected_classes if no_selected else "grow",
                    type="button",
                )["No"],
            ],
        ],
    ]


def _number_produced_input(*, pin: Pin | None) -> list[Element | VoidElement]:
    return _text_field(
        name="number_produced",
        label_text="Number Produced",
        value=pin.number_produced if pin and pin.number_produced else None,
        input_type="number",
        min_value=0,
        step=1,
        placeholder="e.g. 100",
    )


def _release_date_input(*, pin: Pin | None) -> list[Element | VoidElement]:
    return _text_field(
        name="release_date",
        label_text="Release Date",
        value=str(pin.release_date) if pin and pin.release_date else None,
        input_type="date",
    )


def _end_date_input(*, pin: Pin | None) -> list[Element | VoidElement]:
    return _text_field(
        name="end_date",
        label_text="End Date",
        value=str(pin.end_date) if pin and pin.end_date else None,
        input_type="date",
    )


def _funding_input(*, pin: Pin | None) -> list[Element | VoidElement]:
    return [
        label(for_="funding_type")["Funding Type"],
        select(
            name="funding_type",
            id="funding_type",
            class_="single-select w-full min-w-0",
        )[
            [
                option(
                    value=funding_type,
                    selected=funding_type == pin.funding_type if pin else False,
                )[titlecase(funding_type.replace("_", " "))]
                for funding_type in FundingType
            ]
        ],
    ]


def _posts_input(*, pin: Pin | None) -> list[Element | VoidElement]:
    return _text_field(
        name="posts",
        label_text="Posts",
        value=pin.posts if pin else 1,
        input_type="number",
        min_value=1,
        step=1,
    )


def _dimension_field(
    *,
    name: str,
    label_text: str,
    pin: Pin | None,
) -> list[Element | VoidElement]:
    value_mm = getattr(pin, name, None) if pin else None
    return _text_field(
        name=name,
        label_text=label_text,
        value=f"{value_mm}mm" if value_mm else None,
        pattern=MAGNITUDE_INPUT_PATTERN,
        placeholder="e.g. 40mm or 1.5in",
    )


def _width_input(*, pin: Pin | None) -> list[Element | VoidElement]:
    return _dimension_field(name="width", label_text="Width", pin=pin)


def _height_input(*, pin: Pin | None) -> list[Element | VoidElement]:
    return _dimension_field(name="height", label_text="Height", pin=pin)


def _links_input(*, pin: Pin | None) -> Element | Markup:
    pin_links: list[str] = []
    if pin and pin.links:
        pin_links = [link.path for link in pin.links]

    if not pin_links:
        pin_links = [""]

    links_json = json.dumps(pin_links)

    return div(class_="col-span-full")[
        label(for_="links")["Links"],
        Markup(f"""<div class="mt-2" x-data="{{ links: {links_json.replace('"', "'")} }}">
            <template x-for="(link, index) in links" :key="index">
                <div class="grid grid-cols-[1fr_min-content] gap-2 mb-2">
                    <input
                        type="text"
                        name="links"
                        x-model="links[index]"
                        autocomplete="off"
                        placeholder="https://..."
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
                class="w-full mt-2">Add Another Link</button>
        </div>"""),
    ]


def _description_input(*, pin: Pin | None) -> list[Element | VoidElement]:
    return [
        label(for_="md-editor-description", class_="col-span-full")["Description"],
        div(class_="col-span-full min-w-0")[
            markdown_editor(
                field_id="description",
                name="description",
                value=pin.description if pin else None,
            )
        ],
    ]
