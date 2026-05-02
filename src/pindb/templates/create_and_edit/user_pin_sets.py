"""
htpy page and fragment builders: `templates/create_and_edit/user_pin_sets.py`.
"""

from fastapi import Request
from htpy import Element, button, div, form, hr, input

from pindb.templates.base import html_base
from pindb.templates.components.forms.form_field import form_field
from pindb.templates.components.forms.markdown_editor import markdown_editor
from pindb.templates.components.forms.name_availability import (
    name_availability_field,
    name_check_attrs,
)
from pindb.templates.components.layout.centered import centered_div
from pindb.templates.components.layout.page_heading import page_heading


def create_user_set_page(request: Request) -> Element:
    return html_base(
        title="Create Set",
        request=request,
        body_content=centered_div(
            content=[
                page_heading(
                    icon="layout-grid",
                    text="Create Set",
                ),
                hr,
                _create_form(request=request),
            ],
            flex=True,
            col=True,
        ),
    )


def _create_form(request: Request) -> Element:
    name_feedback_id: str = "personal-pin-set-name-availability-feedback"
    return div(class_="flex flex-col gap-2")[
        form(
            method="post",
            action=str(request.url_for("create_personal_set")),
            hx_post=str(request.url_for("create_personal_set")),
            hx_swap="none",
            class_="flex flex-col gap-2",
            **{"data-htmx-submit-guard": ""},
        )[
            form_field(
                label_text="Name",
                field_id="name",
                child=name_availability_field(
                    feedback_id=name_feedback_id,
                    child=input(
                        type="text",
                        id="name",
                        name="name",
                        required=True,
                        autocomplete="off",
                        class_="bg-lighter border border-lightest rounded px-2 py-1 text-base-text",
                        placeholder="My Collection",
                        **name_check_attrs(
                            check_url=str(
                                request.url_for("get_personal_set_check_name")
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
                class_="self-start px-4 py-1 rounded-lg bg-main hover:bg-main-hover border border-lightest cursor-pointer text-base-text w-full",
            )["Create Set"],
        ],
    ]
