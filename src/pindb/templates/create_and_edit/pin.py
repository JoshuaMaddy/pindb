"""
htpy page and fragment builders: `templates/create_and_edit/pin.py`.
"""

import json
import uuid
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
    h2,
    hr,
    i,
    input,
    label,
    option,
    p,
    script,
    select,
    span,
)
from markupsafe import Markup

from pindb.database import Artist, Shop, Tag
from pindb.database.currency import Currency
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.model_utils import MAGNITUDE_INPUT_PATTERN
from pindb.models import AcquisitionType, FundingType
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div
from pindb.templates.components.markdown_editor import markdown_editor
from pindb.templates.components.page_heading import page_heading

with open(
    file=Path(__file__).parent.parent / "js/pin_creation.js",
    mode="r",
    encoding="utf-8",
) as js_file:
    SCRIPT_CONTENT: str = js_file.read()


def pin_form(
    post_url: URL | str,
    currencies: Sequence[Currency],
    shops: Sequence[Shop],
    tags: Sequence[Tag],
    pin_sets: Sequence[PinSet],
    artists: Sequence[Artist],
    options_base_url: str,
    request: Request,
    pin: Pin | None = None,
    duplicate_source: Pin | None = None,
) -> Element:
    """Render the pin create/edit form.

    `pin`              — when present, the form is an edit form for that pin.
    `duplicate_source` — when present (and `pin` is None), prefill values from
                         this pin to seed a new pin. Images are NOT copied;
                         the user must upload fresh images.
    """
    if pin is not None and duplicate_source is not None:
        message = "pin_form: pass either `pin` or `duplicate_source`, not both."
        raise ValueError(message)

    # Source for non-image field values (name, shops, grades, etc.).
    prefill: Pin | None = pin if pin is not None else duplicate_source

    return html_base(
        title="Create Pin" if not pin else "Edit Pin",
        body_content=centered_div(
            content=[
                script[
                    Markup(
                        f"window.PIN_FORM_REF = {json.dumps({'optionsBaseUrl': options_base_url})};"
                    )
                ],
                page_heading(
                    icon="circle-star" if not pin else "pencil",
                    text="Create a Pin" if not pin else "Edit a Pin",
                ),
                duplicate_source is not None
                and _duplicate_notice(source_name=duplicate_source.name),
                _pending_notice(request=request, pin=pin),
                hr,
                form(
                    hx_post=str(post_url),
                    hx_encoding="multipart/form-data",
                    hx_swap="none",
                    enctype="multipart/form-data",
                    class_="grid w-full min-w-0 grid-cols-[1fr_2fr] max-sm:grid-cols-1 gap-2 [&_label]:font-semibold",
                    autocomplete="off",
                )[
                    div(class_="flex flex-col gap-2 min-w-0")[
                        __front_image_input(pin=pin),
                        __back_image_input(pin=pin),
                    ],
                    div(
                        class_="grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-[max-content_1fr] sm:items-start"
                    )[
                        __required_fields(
                            shops=shops,
                            tags=tags,
                            pin=prefill,
                            currencies=currencies,
                            request=request,
                        ),
                        hr(class_="col-span-full"),
                        __optional_fields(
                            pin=prefill,
                            pin_sets=pin_sets,
                            artists=artists,
                        ),
                        input(
                            type="submit",
                            value="Submit",
                            class_="col-span-full mt-2",
                        ),
                    ],
                ],
            ],
        ),
        script_content=SCRIPT_CONTENT,
        request=request,
    )


def _duplicate_notice(source_name: str) -> Element:
    return div(
        class_="rounded bg-blue-900 border border-blue-600 text-blue-200 px-4 py-2 text-sm my-2"
    )[
        i(data_lucide="copy", class_="inline-block w-4 h-4 mr-1"),
        f'Duplicating "{source_name}". Fields are prefilled — upload new images and submit to create the new pin.',
    ]


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
    shops: Sequence[Shop],
    tags: Sequence[Tag],
    currencies: Sequence[Currency],
    request: Request,
    pin: Pin | None = None,
) -> Fragment:
    return fragment[
        h2(class_="col-span-full")["Required"],
        __name_input(pin=pin),
        __shops_input(pin=pin, shops=shops),
        __acquisition_input(pin=pin),
        __grades_input(currencies=currencies, pin=pin),
        __tag_ids_input(pin=pin, tags=tags, request=request),
    ]


def __optional_fields(
    artists: Sequence[Artist],
    pin_sets: Sequence[PinSet],
    pin: Pin | None = None,
) -> Fragment:
    return fragment[
        h2(class_="col-span-full")["Optional"],
        # Images
        __artist_ids_input(pin=pin, artists=artists),
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
        )[
            fragment["Front Image", span(class_="text-red-200 ml-0.5")["*"]]
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


def __back_image_input(pin: Pin | None) -> list[Element | VoidElement]:
    return [
        div(
            class_="image-drop w-full flex flex-col gap-1 aspect-square justify-center items-center border-2 border-pin-border rounded-lg bg-cover bg-no-repeat bg-center transition-all duration-100 cursor-pointer hover:border-accent",
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
    lbl = (
        label(for_=name)[label_text, span(class_="text-red-200 ml-0.5")["*"]]
        if required
        else label(for_=name)[label_text]
    )
    normalized_value: str | int | None = (
        str(value) if isinstance(value, float) else value
    )
    return [
        lbl,
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


def __name_input(pin: Pin | None) -> list[Element | VoidElement]:
    return _text_field(
        name="name",
        label_text="Name",
        value=pin.name if pin else "",
        required=True,
        placeholder="e.g. Cherry Blossom Artist Edition",
    )


def __shops_input(
    shops: Sequence[Shop],
    pin: Pin | None,
) -> list[Element | VoidElement]:
    return [
        label(for_="shop_ids")["Shops", span(class_="text-red-200 ml-0.5")["*"]],
        select(
            name="shop_ids",
            id="shop_ids",
            required=True,
            multiple=True,
            class_="multi-select w-full min-w-0",
            data_entity_type="shop",
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


def __acquisition_input(pin: Pin | None) -> list[Element | VoidElement]:
    return [
        label(for_="acquisition_type")[
            "Acquisition", span(class_="text-red-200 ml-0.5")["*"]
        ],
        select(
            name="acquisition_type",
            id="acquisition_type",
            class_="single-select w-full min-w-0",
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
    # Prepare initial grades data (each row needs a string `id` for Alpine :key)
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

    # Ensure at least one default grade
    if not grades_data:
        grades_data = [{"id": str(uuid.uuid4()), "name": "Normal", "price": ""}]

    # Default currency
    default_currency_id = pin.currency_id if pin else 999

    grades_json = json.dumps(grades_data)

    return [
        label(for_="grade")["Grade", span(class_="text-red-200 ml-0.5")["*"]],
        Markup(f"""<div class="flex w-full min-w-0 flex-wrap gap-2">
            <div class="flex min-w-0 flex-1 flex-col gap-2" x-data="{{ grades: {grades_json.replace('"', "'")} }}">
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
            class_="w-full min-w-0 sm:w-auto sm:min-w-[8rem]",
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


def __tag_ids_input(
    pin: Pin | None,
    tags: Sequence[Tag],
    request: Request,
) -> list[Element | VoidElement]:
    preview_url = str(request.url_for("get_tag_implication_preview"))
    return [
        label(for_="tag_ids")["Tags", span(class_="text-red-200 ml-0.5")["*"]],
        select(
            name="tag_ids",
            id="tag_ids",
            required=True,
            multiple=True,
            class_="multi-select w-full min-w-0",
            data_entity_type="tag",
            hx_get=preview_url,
            # Override form hx_swap="none" — inherited swap would discard preview HTML.
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


def __limited_edition_input(pin: Pin | None) -> list[Element | VoidElement]:
    selected_classes = "bg-pin-main border-accent text-accent grow"
    yes_selected = pin is not None and pin.limited_edition is True
    no_selected = pin is not None and pin.limited_edition is False
    le_input_kwargs: dict[str, object] = {
        "name": "limited_edition",
        "id": "limited_edition",
        "type": "checkbox",
        "class_": "self-start",
        "hidden": True,
    }
    # Unchecked checkboxes are omitted from POST; when Yes/No is known we keep the
    # box checked so `true` / `false` is submitted (see pin_creation.js).
    if pin is not None and pin.limited_edition is not None:
        le_input_kwargs["checked"] = True
        le_input_kwargs["value"] = "true" if pin.limited_edition else "false"

    return [
        label(for_="limited_edition")["Limited Edition"],
        div(class_="flex w-full min-w-0 flex-col gap-2")[
            input(**le_input_kwargs),
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


def __number_produced_input(pin: Pin | None) -> list[Element | VoidElement]:
    return _text_field(
        name="number_produced",
        label_text="Number Produced",
        value=pin.number_produced if pin and pin.number_produced else None,
        input_type="number",
        min_value=0,
        step=1,
        placeholder="e.g. 100",
    )


def __release_date_input(pin: Pin | None) -> list[Element | VoidElement]:
    return _text_field(
        name="release_date",
        label_text="Release Date",
        value=str(pin.release_date) if pin and pin.release_date else None,
        input_type="date",
    )


def __end_date_input(pin: Pin | None) -> list[Element | VoidElement]:
    return _text_field(
        name="end_date",
        label_text="End Date",
        value=str(pin.end_date) if pin and pin.end_date else None,
        input_type="date",
    )


def __funding_input(pin: Pin | None) -> list[Element | VoidElement]:
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
                )[funding_type.replace("_", " ").title()]
                for funding_type in FundingType
            ]
        ],
    ]


def __posts_input(pin: Pin | None) -> list[Element | VoidElement]:
    return _text_field(
        name="posts",
        label_text="Posts",
        value=pin.posts if pin else 1,
        input_type="number",
        min_value=1,
        step=1,
    )


def _dimension_field(
    *, name: str, label_text: str, pin: Pin | None
) -> list[Element | VoidElement]:
    value_mm = getattr(pin, name, None) if pin else None
    return _text_field(
        name=name,
        label_text=label_text,
        value=f"{value_mm}mm" if value_mm else None,
        pattern=MAGNITUDE_INPUT_PATTERN,
        placeholder="e.g. 40mm or 1.5in",
    )


def __width_input(pin: Pin | None) -> list[Element | VoidElement]:
    return _dimension_field(name="width", label_text="Width", pin=pin)


def __height_input(pin: Pin | None) -> list[Element | VoidElement]:
    return _dimension_field(name="height", label_text="Height", pin=pin)


def __links_input(pin: Pin | None) -> Element | Markup:
    pin_links: list[str] = []
    if pin and pin.links:
        pin_links = [link.path for link in pin.links]

    # Ensure at least one empty field
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


def __description_input(pin: Pin | None) -> list[Element | VoidElement]:
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
