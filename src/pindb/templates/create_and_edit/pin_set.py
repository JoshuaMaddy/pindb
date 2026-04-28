"""
htpy page and fragment builders: `templates/create_and_edit/pin_set.py`.
"""

import json

from fastapi import Request
from htpy import (
    Element,
    a,
    button,
    div,
    form,
    h2,
    hr,
    i,
    img,
    input,
    p,
    script,
    span,
)
from markupsafe import Markup

from pindb.database.pin import Pin
from pindb.database.pin_set import PinSet
from pindb.database.user import User
from pindb.templates.base import html_base
from pindb.templates.components.dialogs.confirm_modal import confirm_modal
from pindb.templates.components.display.empty_state import empty_state
from pindb.templates.components.forms.form_field import form_field
from pindb.templates.components.forms.htmx_search_input import htmx_search_input
from pindb.templates.components.forms.icon_button import icon_button
from pindb.templates.components.forms.markdown_editor import markdown_editor
from pindb.templates.components.forms.name_availability import (
    name_availability_field,
    name_check_attrs,
)
from pindb.templates.components.forms.toggle_button import toggle_button
from pindb.templates.components.layout.centered import centered_div
from pindb.templates.components.layout.page_heading import page_heading
from pindb.templates.pin_image_alt import pin_front_image_alt

# ---------------------------------------------------------------------------
# Admin create page
# ---------------------------------------------------------------------------


def pin_set_create_page(request: Request) -> Element:
    name_feedback_id: str = "pin-set-name-availability-feedback"
    gate_cfg = {
        "formId": "pin-set-create-form",
        "submitId": "pin-set-create-submit",
        "fields": [
            {
                "key": "name",
                "kind": "text",
                "inputId": "name",
                "hint": "Enter a name for this pin set.",
                "highlightSelector": '[data-pin-field="name"]',
            }
        ],
    }
    gate_json = json.dumps(gate_cfg).replace("</", "<\\/")

    return html_base(
        title="Create Pin Set",
        request=request,
        template_js_extra=("forms/entity_form_gate.js",),
        body_content=centered_div(
            content=[
                page_heading(
                    icon="layout-grid",
                    text="Create Pin Set",
                ),
                hr,
                script(**{"type": "application/json"}, id="entity-form-gate-data")[
                    Markup(gate_json)
                ],
                form(
                    id="pin-set-create-form",
                    method="post",
                    action=str(request.url_for("post_create_pin_set")),
                    hx_post=str(request.url_for("post_create_pin_set")),
                    hx_swap="none",
                    class_="flex flex-col gap-2",
                )[
                    form_field(
                        label_text="Name",
                        field_id="name",
                        required=True,
                        child=name_availability_field(
                            feedback_id=name_feedback_id,
                            data_pin_field="name",
                            child=input(
                                type="text",
                                id="name",
                                name="name",
                                required=True,
                                autocomplete="off",
                                class_="bg-lighter border border-lightest rounded px-2 py-1 text-base-text",
                                placeholder="Set Name",
                                **name_check_attrs(
                                    check_url=str(
                                        request.url_for("get_create_check_name")
                                    ),
                                    kind="pin_set",
                                    target_id=name_feedback_id,
                                ),
                            ),
                        ),
                    ),
                    form_field(
                        label_text="Description",
                        field_id="md-editor-description",
                        child=markdown_editor(
                            field_id="description",
                            name="description",
                        ),
                    ),
                    button(
                        type="submit",
                        id="pin-set-create-submit",
                        formnovalidate=True,
                        class_="self-start px-4 py-1 rounded-lg bg-main hover:bg-main-hover border border-lightest cursor-pointer text-base-text w-full transition-opacity",
                    )["Create Set"],
                ],
            ],
            flex=True,
            col=True,
        ),
    )


# ---------------------------------------------------------------------------
# Rich edit page (personal and global sets)
# ---------------------------------------------------------------------------


def pin_set_edit_page(
    request: Request,
    pin_set: PinSet,
    pins: list[Pin],
    current_user: User,
) -> Element:
    reorder_url = str(request.url_for("reorder_set_pins", set_id=pin_set.id))
    is_global: bool = pin_set.owner_id is None

    if is_global:
        back_href = str(request.url_for("get_list_pin_sets"))
        back_label = "Pin Sets"
    else:
        back_href = str(
            request.url_for("get_user_profile", username=current_user.username)
        )
        back_label = "My Profile"

    header_extras: list[Element] = [
        icon_button(
            icon="eye",
            title="View",
            href=str(request.url_for("get_pin_set", id=pin_set.id)),
        )
    ]

    if current_user.is_admin and not is_global:
        promote_url = str(request.url_for("promote_set_to_global", set_id=pin_set.id))
        header_extras.append(
            confirm_modal(
                trigger=icon_button(icon="globe", title="Promote to global"),
                message=f'Promote "{pin_set.name}" to a global set? It will become admin-only and visible to all users.',
                form_action=promote_url,
                confirm_label="Promote",
                htmx_post=True,
            )
        )

    return html_base(
        title=f"Edit — {pin_set.name}",
        request=request,
        template_js_extra=("pins/pin_set_sortable.js",),
        body_content=centered_div(
            content=[
                a(
                    href=back_href,
                    class_="text-lightest-hover no-underline hover:text-accent",
                )[
                    i(data_lucide="arrow-left", class_="inline-block mb-1"),
                    f" {back_label}",
                ],
                page_heading(
                    icon="pencil",
                    text=f"Edit: {pin_set.name}",
                    extras=header_extras,
                ),
                hr,
                _metadata_form(request=request, pin_set=pin_set),
                hr,
                pin_list_section(
                    request=request,
                    pin_set=pin_set,
                    pins=pins,
                    reorder_url=reorder_url,
                ),
                hr,
                _add_pin_section(request=request, pin_set=pin_set),
            ],
            flex=True,
            col=True,
        ),
    )


def _metadata_form(request: Request, pin_set: PinSet) -> Element:
    name_feedback_id: str = "pin-set-name-availability-feedback"
    check_url: str = str(
        request.url_for("get_create_check_name")
        if pin_set.owner_id is None
        else request.url_for("get_personal_set_check_name")
    )
    return div(class_="flex flex-col gap-2")[
        h2["Details"],
        form(
            method="post",
            action=str(request.url_for("update_set", set_id=pin_set.id)),
            hx_post=str(request.url_for("update_set", set_id=pin_set.id)),
            hx_swap="none",
            class_="flex flex-col gap-2",
        )[
            form_field(
                label_text="Name",
                field_id="name",
                required=True,
                child=name_availability_field(
                    feedback_id=name_feedback_id,
                    child=input(
                        type="text",
                        id="name",
                        name="name",
                        value=pin_set.name,
                        required=True,
                        autocomplete="off",
                        class_="bg-lighter border border-lightest rounded px-2 py-1 text-base-text",
                        **name_check_attrs(
                            check_url=check_url,
                            kind="pin_set",
                            target_id=name_feedback_id,
                            exclude_id=pin_set.id,
                        ),
                    ),
                ),
            ),
            form_field(
                label_text="Description",
                field_id="md-editor-description",
                child=markdown_editor(
                    field_id="description",
                    name="description",
                    value=pin_set.description,
                ),
            ),
            button(
                type="submit",
                class_="self-start px-4 py-1 rounded-lg bg-main hover:bg-main-hover border border-lightest cursor-pointer text-base-text w-full",
            )["Save"],
        ],
    ]


def pin_list_section(
    request: Request,
    pin_set: PinSet,
    pins: list[Pin],
    reorder_url: str,
) -> Element:
    return div(id="pin-list-section", class_="flex flex-col gap-2")[
        h2(id="pin-list-count")[f"Pins ({len(pins)})"],
        pins and p(class_="text-sm text-lightest-hover")["Drag cards to reorder."],
        div(
            id="pin-list",
            data_reorder_url=reorder_url,
            class_="flex flex-wrap gap-2",
        )[
            *(
                [_pin_card(request=request, pin=pin, set_id=pin_set.id) for pin in pins]
                or [
                    p(id="pin-list-empty", class_="text-lightest-hover")[
                        "No pins in this set yet."
                    ]
                ]
            )
        ],
    ]


def pin_count_oob(count: int) -> Element:
    """OOB fragment that updates the Pins (n) heading."""
    return h2(id="pin-list-count", hx_swap_oob="true")[f"Pins ({count})"]


def pin_card_oob(request: Request, pin: Pin, set_id: int) -> Element:
    """OOB fragment that appends a new pin card to #pin-list."""
    return div(hx_swap_oob="beforeend:#pin-list")[
        _pin_card(request=request, pin=pin, set_id=set_id)
    ]


def pin_empty_oob() -> Element:
    """OOB fragment that deletes the empty-state placeholder from #pin-list."""
    return p(id="pin-list-empty", hx_swap_oob="delete")


def _pin_card(request: Request, pin: Pin, set_id: int) -> Element:
    remove_url = str(
        request.url_for("remove_pin_from_personal_set", set_id=set_id, pin_id=pin.id)
    )
    image_url = str(
        request.url_for("get_image", guid=pin.front_image_guid).include_query_params(
            thumbnail=True
        )
    )
    return div(
        id=f"pin-row-{pin.id}",
        data_pin_id=str(pin.id),
        class_="relative flex flex-col w-25 shrink-0 rounded-lg bg-lighter border border-lightest overflow-hidden cursor-grab select-none hover:border-accent",
    )[
        button(
            type="button",
            aria_label="Remove pin from set",
            hx_delete=remove_url,
            hx_target=f"#pin-row-{pin.id}",
            hx_swap="outerHTML",
            class_="absolute top-1 right-1 z-10 flex items-center justify-center w-5 h-5 rounded-full bg-main border border-error-dark cursor-pointer text-error-main hover:text-error-main-hover hover:border-error-dark-hover p-0",
        )[i(data_lucide="x", class_="w-3 h-3", aria_hidden="true")],
        a(
            href=str(
                request.url_for("get_pin", id=pin.id).include_query_params(
                    back=str(request.url)
                )
            ),
            class_="block",
            tabindex="-1",
        )[
            img(
                src=image_url,
                alt=pin_front_image_alt(pin),
                class_="w-full aspect-square object-contain bg-main",
            )
        ],
        p(class_="px-2 pt-1 pb-0 text-xs text-base-text leading-tight line-clamp-2")[
            pin.name
        ],
        div(class_="flex justify-center pb-1 pt-0.5 text-lightest-hover")[
            i(data_lucide="grip-horizontal", class_="w-4 h-4"),
        ],
    ]


def _add_pin_section(request: Request, pin_set: PinSet) -> Element:
    search_url = str(request.url_for("search_pins_for_set", set_id=pin_set.id))
    return div(class_="flex flex-col gap-2")[
        h2["Add Pins"],
        htmx_search_input(
            search_url, "#pin-search-results", placeholder="Search pins by name…"
        ),
        div(id="pin-search-results"),
    ]


# ---------------------------------------------------------------------------
# HTMX fragment: search results returned by search_pins_for_set route
# ---------------------------------------------------------------------------


def pin_search_results(
    request: Request,
    set_id: int,
    pins: list[Pin],
    existing_ids: set[int],
) -> Element:
    if not pins:
        return empty_state("No results.", small=True)

    return div(class_="flex flex-col gap-1")[
        *[
            search_result_row(
                request=request,
                pin=pin,
                set_id=set_id,
                in_set=pin.id in existing_ids,
            )
            for pin in pins
        ]
    ]


def search_result_row(
    request: Request,
    pin: Pin,
    set_id: int,
    in_set: bool,
) -> Element:
    if in_set:
        action_url = str(
            request.url_for(
                "remove_pin_from_personal_set", set_id=set_id, pin_id=pin.id
            )
        )
        icon = "check-square"
        text_class = "text-lightest-hover"
    else:
        action_url = str(
            request.url_for("add_pin_to_personal_set", set_id=set_id, pin_id=pin.id)
        )
        icon = "square"
        text_class = "text-base-text"

    thumbnail_url = str(
        request.url_for("get_image", guid=pin.front_image_guid).include_query_params(
            thumbnail=True
        )
    )
    shops = sorted(pin.shops, key=lambda s: s.name)
    artists = sorted(pin.artists, key=lambda a: a.name)
    shop_text = (shops[0].name + (" …" if len(shops) > 1 else "")) if shops else None
    artist_text = (
        (artists[0].name + (" …" if len(artists) > 1 else "")) if artists else None
    )
    return div(
        id=f"search-row-{pin.id}",
        class_="flex items-center gap-2 p-2 rounded bg-lighter border border-lightest",
    )[
        toggle_button(
            url=action_url,
            is_active=in_set,
            target_id=f"search-row-{pin.id}",
            children=[
                i(data_lucide=icon, class_="inline-block shrink-0"),
                img(
                    src=thumbnail_url,
                    alt=pin_front_image_alt(pin),
                    class_="w-10 h-10 object-contain rounded bg-main shrink-0",
                ),
                div(class_="flex flex-col gap-0.5 flex-1 min-w-0")[
                    span(class_="truncate")[pin.name],
                    bool(shop_text or artist_text)
                    and div(class_="flex gap-3 text-xs text-lightest-hover")[
                        bool(shop_text) and span[shop_text],
                        bool(artist_text) and span[artist_text],
                    ],
                ],
            ],
            class_=f"flex items-center gap-2 flex-1 bg-transparent border-0 cursor-pointer text-left font-inherit p-0 {text_class}",
        )
    ]
