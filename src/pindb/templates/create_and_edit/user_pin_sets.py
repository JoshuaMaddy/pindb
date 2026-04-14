from fastapi import Request
from htpy import Element, button, div, form, hr, input

from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div
from pindb.templates.components.form_field import form_field
from pindb.templates.components.markdown_editor import markdown_editor
from pindb.templates.components.page_heading import page_heading


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
    return div(class_="flex flex-col gap-2")[
        form(
            method="post",
            action=str(request.url_for("create_personal_set")),
            class_="flex flex-col gap-2",
        )[
            form_field(
                label_text="Name",
                field_id="name",
                child=input(
                    type="text",
                    id="name",
                    name="name",
                    required=True,
                    class_="bg-pin-base-450 border border-pin-base-400 rounded px-2 py-1 text-pin-base-text",
                    placeholder="My Collection",
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
                class_="self-start px-4 py-1 rounded-lg bg-pin-main hover:bg-pin-main-hover border border-pin-base-400 cursor-pointer text-pin-base-text w-full",
            )["Create Set"],
        ],
    ]
