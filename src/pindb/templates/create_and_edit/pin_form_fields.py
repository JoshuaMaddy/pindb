"""
Field builders for the pin create/edit form.
"""

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
from pindb.templates.components.islands import island
from pindb.utils import review_label


def _enhanced_select(
    select_element: Element,
    *,
    select_id: str,
    load_url: str = "",
    create: bool = False,
    tag_mode: bool = False,
    single_mode: bool = False,
    placeholder: str = "",
) -> Element:
    """Server-rendered select + the ``multi-select`` island that enhances it.

    The island adopts the select at mount (moves it inside itself, hidden);
    the select stays the form-submitting element, so names, HTMX triggers
    and server routes are untouched. Wrapped in one div so [label, widget]
    field pairs keep their two-column grid placement.
    """
    props: dict[str, object] = {"selectId": select_id}
    if load_url:
        props["loadUrl"] = load_url
    if create:
        props["create"] = True
    if tag_mode:
        props["tagMode"] = True
    if single_mode:
        props["singleMode"] = True
    if placeholder:
        props["placeholder"] = placeholder
    return div(class_="w-full min-w-0")[
        select_element,
        island("multi-select", props=props),
    ]


def _required_fields(
    *,
    shops: Sequence[Shop],
    tags: Sequence[Tag],
    currencies: Sequence[Currency],
    request: Request,
    options_base_url: str,
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
        _shops_input(pin=pin, shops=shops, options_base_url=options_base_url),
        _acquisition_input(pin=pin),
        _grades_input(currencies=currencies, pin=pin),
        _tag_ids_input(
            pin=pin, tags=tags, request=request, options_base_url=options_base_url
        ),
    ]


def _optional_fields(
    *,
    artists: Sequence[Artist],
    pin_sets: Sequence[PinSet],
    variant_pins: Sequence[Pin],
    unauthorized_copy_pins: Sequence[Pin],
    options_base_url: str,
    pin: Pin | None = None,
    exclude_pin_id: int | None = None,
) -> Fragment:
    # Exclude only the pin being edited (not a duplicate's source — the
    # duplicate may legitimately become a variant of it).
    exclude_query = f"?exclude={exclude_pin_id}" if exclude_pin_id is not None else ""
    pin_load_url = f"{options_base_url}/pin{exclude_query}"
    return fragment[
        h2(class_="col-span-full")["Optional"],
        _artist_ids_input(pin=pin, artists=artists, options_base_url=options_base_url),
        _pin_sets_ids_input(
            pin=pin, pin_sets=pin_sets, options_base_url=options_base_url
        ),
        _variant_pins_input(pin=pin, variant_pins=variant_pins, load_url=pin_load_url),
        _unauthorized_copy_pins_input(
            pin=pin,
            unauthorized_copy_pins=unauthorized_copy_pins,
            load_url=pin_load_url,
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


def _pin_images_input(*, pin: Pin | None) -> list[Element | VoidElement]:
    """Svelte ``pin-images`` island + the server-rendered file inputs it drives.

    The hidden inputs stay outside the island so their files ride the normal
    multipart form submit; the island syncs picked/dropped/pasted files into
    them via ``DataTransfer`` after client-side WebP transcode.
    """
    front_url: str | None = f"/get/image/{pin.front_image_guid}" if pin else None
    back_url: str | None = (
        f"/get/image/{pin.back_image_guid}" if pin and pin.back_image_guid else None
    )
    return [
        island(
            "pin-images",
            props={
                "front": {"existingUrl": front_url},
                "back": {"existingUrl": back_url},
            },
            class_="contents",
        ),
        input(
            type="file",
            id="front_image",
            name="front_image",
            accept="image/png, image/jpeg, image/jpg, image/webp",
            required=True if not pin else False,
            class_="hidden",
            hidden=True,
        ),
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
    options_base_url: str,
) -> list[Element | VoidElement]:
    return [
        label(for_="shop_ids")["Shops", span(class_="text-error-main ml-0.5")["*"]],
        _enhanced_select(
            select(
                name="shop_ids",
                id="shop_ids",
                required=True,
                multiple=True,
                class_="w-full min-w-0",
                data_pin_field="shops",
            )[
                [
                    option(
                        value=str(shop.id),
                        selected=shop in pin.shops if pin else False,
                    )[
                        review_label(
                            shop.name,
                            is_pending=shop.is_pending,
                            is_rejected=shop.is_rejected,
                        )
                    ]
                    for shop in shops
                ]
            ],
            select_id="shop_ids",
            load_url=f"{options_base_url}/shop",
        ),
    ]


def _acquisition_input(*, pin: Pin | None) -> list[Element | VoidElement]:
    return [
        label(for_="acquisition_type")[
            "Acquisition", span(class_="text-error-main ml-0.5")["*"]
        ],
        _enhanced_select(
            select(
                name="acquisition_type",
                id="acquisition_type",
                class_="w-full min-w-0",
                required=True,
                data_pin_field="acquisition",
            )[
                [
                    option(
                        value=acquisition_type,
                        selected=acquisition_type == pin.acquisition_type
                        if pin
                        else False,
                    )[titlecase(acquisition_type.replace("_", " "))]
                    for acquisition_type in AcquisitionType
                ]
            ],
            select_id="acquisition_type",
        ),
    ]


def _grades_input(
    *,
    currencies: Sequence[Currency],
    pin: Pin | None,
) -> list[Element | VoidElement]:
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

    return [
        label(for_="grade")["Grade", span(class_="text-error-main ml-0.5")["*"]],
        div(class_="flex w-full min-w-0 flex-wrap gap-2")[
            island(
                "grades-editor",
                props={"grades": grades_data},
                id="pin-grade-section",
                class_="flex min-w-0 flex-1 flex-col gap-2",
            ),
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
        ],
    ]


def _tag_ids_input(
    *,
    pin: Pin | None,
    tags: Sequence[Tag],
    request: Request,
    options_base_url: str,
) -> list[Element | VoidElement]:
    preview_url = str(request.url_for("get_tag_implication_preview"))
    return [
        label(for_="tag_ids")["Tags", span(class_="text-error-main ml-0.5")["*"]],
        _enhanced_select(
            select(
                name="tag_ids",
                id="tag_ids",
                required=True,
                multiple=True,
                class_="w-full min-w-0",
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
                    )[
                        review_label(
                            tag.display_name,
                            is_pending=tag.is_pending,
                            is_rejected=tag.is_rejected,
                        )
                    ]
                    for tag in sorted(tags, key=lambda tag: (tag.category, tag.name))
                ]
            ],
            select_id="tag_ids",
            load_url=f"{options_base_url}/tag",
            tag_mode=True,
        ),
        div(id="implication-preview", class_="col-span-full"),
    ]


def _artist_ids_input(
    *,
    pin: Pin | None,
    artists: Sequence[Artist],
    options_base_url: str,
) -> list[Element | VoidElement]:
    return [
        label(for_="artist_ids")["Artists"],
        _enhanced_select(
            select(
                name="artist_ids",
                id="artist_ids",
                multiple=True,
                class_="w-full min-w-0",
            )[
                [
                    option(
                        value=str(artist.id),
                        selected=artist in pin.artists if pin else False,
                    )[
                        review_label(
                            artist.name,
                            is_pending=artist.is_pending,
                            is_rejected=artist.is_rejected,
                        )
                    ]
                    for artist in artists
                ]
            ],
            select_id="artist_ids",
            load_url=f"{options_base_url}/artist",
        ),
    ]


def _pin_sets_ids_input(
    *,
    pin: Pin | None,
    pin_sets: Sequence[PinSet],
    options_base_url: str,
) -> list[Element | VoidElement]:
    return [
        label(for_="pin_sets_ids")["Pin Sets"],
        _enhanced_select(
            select(
                name="pin_sets_ids",
                id="pin_sets_ids",
                multiple=True,
                class_="w-full min-w-0",
            )[
                [
                    option(
                        value=str(pin_set.id),
                        selected=pin_set in pin.sets if pin else False,
                    )[
                        review_label(
                            pin_set.name,
                            is_pending=pin_set.is_pending,
                            is_rejected=pin_set.is_rejected,
                        )
                    ]
                    for pin_set in pin_sets
                ]
            ],
            select_id="pin_sets_ids",
            load_url=f"{options_base_url}/pin_set",
        ),
    ]


def _pin_option(*, pin_obj: Pin) -> Element:
    return option(
        value=str(pin_obj.id),
        selected=True,
        data_thumbnail=f"/get/image/{pin_obj.front_image_guid}?w=100",
    )[
        review_label(
            pin_obj.name, is_pending=pin_obj.is_pending, is_rejected=pin_obj.is_rejected
        )
    ]


def _variant_pins_input(
    *,
    pin: Pin | None,
    variant_pins: Sequence[Pin],
    load_url: str,
) -> list[Element | VoidElement]:
    return [
        label(for_="variant_pin_ids")["Variants"],
        _enhanced_select(
            select(
                name="variant_pin_ids",
                id="variant_pin_ids",
                multiple=True,
                class_="w-full min-w-0",
            )[[_pin_option(pin_obj=variant) for variant in variant_pins]],
            select_id="variant_pin_ids",
            load_url=load_url,
        ),
    ]


def _unauthorized_copy_pins_input(
    *,
    pin: Pin | None,
    unauthorized_copy_pins: Sequence[Pin],
    load_url: str,
) -> list[Element | VoidElement]:
    return [
        label(for_="unauthorized_copy_pin_ids")["Unauthorized Copies"],
        _enhanced_select(
            select(
                name="unauthorized_copy_pin_ids",
                id="unauthorized_copy_pin_ids",
                multiple=True,
                class_="w-full min-w-0",
            )[[_pin_option(pin_obj=copy_pin) for copy_pin in unauthorized_copy_pins]],
            select_id="unauthorized_copy_pin_ids",
            load_url=load_url,
        ),
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
        _enhanced_select(
            select(
                name="funding_type",
                id="funding_type",
                class_="w-full min-w-0",
            )[
                [
                    option(
                        value=funding_type,
                        selected=funding_type == pin.funding_type if pin else False,
                    )[titlecase(funding_type.replace("_", " "))]
                    for funding_type in FundingType
                ]
            ],
            select_id="funding_type",
        ),
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


def _links_input(*, pin: Pin | None) -> Element:
    pin_links: list[str] = []
    if pin and pin.links:
        pin_links = [link.path for link in pin.links]

    if not pin_links:
        pin_links = [""]

    return div(class_="col-span-full")[
        label(for_="links")["Links"],
        island(
            "links-editor",
            props={"links": pin_links, "placeholder": "https://..."},
            class_="mt-2",
        ),
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
