from fastapi import Request
from htpy import Element, a, button, div, form, h2, hr, input, p, textarea

from pindb.database.pin_set import PinSet
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div
from pindb.templates.components.confirm_modal import confirm_modal
from pindb.templates.components.empty_state import empty_state
from pindb.templates.components.form_field import form_field
from pindb.templates.components.icon_button import icon_button
from pindb.templates.components.page_heading import page_heading


def user_pin_sets_page(
    request: Request,
    sets: list[PinSet],
) -> Element:
    return html_base(
        title="My Sets",
        request=request,
        body_content=centered_div(
            content=[
                page_heading(
                    icon="folder",
                    text="My Sets",
                    gap=3,
                ),
                hr,
                _create_form(request=request),
                hr,
                _sets_list(
                    request=request,
                    sets=sets,
                ),
            ],
            flex=True,
            col=True,
        ),
    )


def _create_form(request: Request) -> Element:
    return div(class_="flex flex-col gap-2")[
        h2["Create New Set"],
        form(
            method="post",
            action=str(request.url_for("create_personal_set")),
            class_="flex flex-col gap-3",
        )[
            form_field(
                label_text="Name",
                field_id="name",
                child=input(
                    type_="text",
                    id="name",
                    name="name",
                    required=True,
                    class_="bg-pin-base-450 border border-pin-base-400 rounded px-3 py-1 text-pin-base-text",
                    placeholder="My Collection",
                ),
            ),
            form_field(
                label_text="Description",
                field_id="description",
                child=textarea(
                    id="description",
                    name="description",
                    rows="2",
                    class_="bg-pin-base-450 border border-pin-base-400 rounded px-3 py-1 text-pin-base-text resize-none",
                    placeholder="Optional description",
                ),
            ),
            button(
                type_="submit",
                class_="self-start px-4 py-1 rounded-lg bg-pin-main hover:bg-pin-main-hover border border-pin-base-400 cursor-pointer text-pin-base-text w-full",
            )["Create Set"],
        ],
    ]


def _sets_list(request: Request, sets: list[PinSet]) -> Element:
    if not sets:
        return empty_state("No sets yet — create one above.")

    return div(class_="flex flex-col gap-3")[
        *[_set_row(request=request, pin_set=ps) for ps in sets]
    ]


def _set_row(request: Request, pin_set: PinSet) -> Element:
    return div(
        class_="flex items-center justify-between gap-4 p-3 rounded-lg bg-pin-base-450 border border-pin-base-400"
    )[
        div(class_="flex flex-col gap-0")[
            a(
                href=str(request.url_for("get_pin_set", id=pin_set.id)),
                class_="font-semibold",
            )[pin_set.name],
            pin_set.description
            and p(class_="text-sm text-pin-base-300")[pin_set.description],
        ],
        div(class_="flex gap-2 shrink-0")[
            icon_button(
                icon="pencil",
                title="Edit set",
                href=str(request.url_for("get_edit_set", set_id=pin_set.id)),
            ),
            confirm_modal(
                trigger=icon_button(
                    icon="trash-2",
                    title="Delete set",
                    variant="danger",
                ),
                message=f'Delete the set "{pin_set.name}"? This won\'t delete any pins.',
                form_action=str(
                    request.url_for("delete_personal_set", set_id=pin_set.id)
                ),
            ),
        ],
    ]
