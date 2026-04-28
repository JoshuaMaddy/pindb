"""
htpy page and fragment builders: `templates/create_and_edit/pin.py`.
"""

import json
from typing import Sequence

from fastapi import Request
from fastapi.datastructures import URL
from htpy import (
    Element,
    button,
    div,
    form,
    hr,
    i,
    input,
    script,
)
from markupsafe import Markup

from pindb.database import Artist, Shop, Tag
from pindb.database.currency import Currency
from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div
from pindb.templates.components.page_heading import page_heading
from pindb.templates.create_and_edit.pin_form_fields import (
    _back_image_input,
    _front_image_input,
    _optional_fields,
    _required_fields,
)


def pin_form(
    post_url: URL | str,
    currencies: Sequence[Currency],
    shops: Sequence[Shop],
    tags: Sequence[Tag],
    pin_sets: Sequence[PinSet],
    artists: Sequence[Artist],
    variant_pins: Sequence[Pin],
    unauthorized_copy_pins: Sequence[Pin],
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
    pin_form_ref_json = json.dumps(
        {
            "optionsBaseUrl": options_base_url,
            "excludePinId": pin.id if pin is not None else None,
            "requireFrontImage": pin is None,
        }
    ).replace("</", "<\\/")

    return html_base(
        title="Create Pin" if not pin else "Edit Pin",
        template_js_extra=("pin_creation.js",),
        body_content=centered_div(
            content=[
                script(**{"type": "application/json"}, id="pin-form-ref-data")[
                    Markup(pin_form_ref_json)
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
                    id="pin-form",
                    hx_post=str(post_url),
                    hx_encoding="multipart/form-data",
                    hx_swap="none",
                    enctype="multipart/form-data",
                    class_="grid w-full min-w-0 grid-cols-[1fr_2fr] max-sm:grid-cols-1 gap-2 [&_label]:font-semibold",
                    autocomplete="off",
                )[
                    div(class_="flex flex-col gap-2 min-w-0")[
                        _front_image_input(pin=pin),
                        _back_image_input(pin=pin),
                    ],
                    div(
                        class_="grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-[max-content_1fr] sm:items-start"
                    )[
                        _required_fields(
                            shops=shops,
                            tags=tags,
                            pin=prefill,
                            currencies=currencies,
                            request=request,
                            name_check_exclude_id=pin.id if pin is not None else None,
                        ),
                        hr(class_="col-span-full"),
                        _optional_fields(
                            pin=prefill,
                            pin_sets=pin_sets,
                            artists=artists,
                            variant_pins=variant_pins,
                            unauthorized_copy_pins=unauthorized_copy_pins,
                        ),
                        button(
                            type="submit",
                            id="pin-form-submit",
                            formnovalidate=True,
                            class_=(
                                "col-span-full mt-2 px-4 py-2 rounded-lg bg-main "
                                "hover:bg-main-hover border border-lightest "
                                "cursor-pointer text-base-text w-full transition-opacity"
                            ),
                        )["Submit"],
                    ],
                ],
            ],
        ),
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
        class_="rounded bg-pending-dark border border-pending-dark text-pending-main px-4 py-2 text-sm my-2"
    )[
        i(data_lucide="clock", class_="inline-block w-4 h-4 mr-1"),
        msg,
    ]
