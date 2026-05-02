"""
htpy page and fragment builders: `templates/create_and_edit/tag.py`.
"""

import json

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
    label,
    option,
    script,
    select,
    span,
)
from markupsafe import Markup
from titlecase import titlecase

from pindb.database.tag import Tag, TagCategory
from pindb.templates.base import html_base
from pindb.templates.components.forms.markdown_editor import markdown_editor
from pindb.templates.components.forms.name_availability import (
    name_availability_field,
    name_check_attrs,
)
from pindb.templates.components.layout.centered import centered_div
from pindb.templates.components.layout.page_heading import page_heading
from pindb.templates.components.tags.tag_branding import CATEGORY_COLORS, CATEGORY_ICONS


def _duplicate_notice(source_display_name: str) -> Element:
    return div(
        class_="rounded bg-blue-900 border border-blue-600 text-blue-200 px-4 py-2 text-sm my-2"
    )[
        i(data_lucide="copy", class_="inline-block w-4 h-4 mr-1"),
        f'Duplicating "{source_display_name}". Fields are prefilled — change the name if needed and submit to create the new tag.',
    ]


def tag_form(
    post_url: URL | str,
    request: Request,
    options_url: str,
    tag: Tag | None = None,
    duplicate_source: Tag | None = None,
) -> Element:
    """Render the tag create/edit form.

    ``tag`` — when present, edit that tag. ``duplicate_source`` — when present
    (and ``tag`` is None), prefill a new tag from this row.
    """
    if tag is not None and duplicate_source is not None:
        message = "tag_form: pass either `tag` or `duplicate_source`, not both."
        raise ValueError(message)

    prefill: Tag | None = tag if tag is not None else duplicate_source
    selected_implications: list[Tag] = list(prefill.implications) if prefill else []
    current_aliases: list[str] = [a.alias for a in prefill.aliases] if prefill else []
    name_feedback_id: str = "tag-name-availability-feedback"
    gate_cfg = {
        "formId": "tag-form",
        "submitId": "tag-form-submit",
        "fields": [
            {
                "key": "name",
                "kind": "text",
                "inputId": "name",
                "hint": "Enter a tag name.",
                "highlightSelector": '[data-pin-field="name"]',
            }
        ],
    }
    gate_json = json.dumps(gate_cfg).replace("</", "<\\/")

    return html_base(
        title="Create Tag" if not tag else "Edit Tag",
        template_js_extra=("tags/tag_form.js", "forms/entity_form_gate.js"),
        body_content=centered_div(
            content=[
                page_heading(
                    icon="tag" if not tag else "pencil",
                    text="Create a Tag" if not tag else "Edit a Tag",
                ),
                duplicate_source is not None
                and _duplicate_notice(
                    source_display_name=duplicate_source.display_name,
                ),
                hr,
                script(**{"type": "application/json"}, id="entity-form-gate-data")[
                    Markup(gate_json)
                ],
                form(
                    id="tag-form",
                    hx_post=str(post_url),
                    hx_target="#pindb-toast-host",
                    hx_swap="innerHTML",
                    class_="flex flex-col gap-2 [&_label]:font-semibold",
                    **{"data-htmx-submit-guard": ""},
                )[
                    label(for_="name")[
                        "Name", span(class_="text-error-main ml-0.5")["*"]
                    ],
                    name_availability_field(
                        feedback_id=name_feedback_id,
                        data_pin_field="name",
                        child=input(
                            type="text",
                            name="name",
                            id="name",
                            required=True,
                            autocomplete="off",
                            value=prefill.display_name if prefill else None,
                            **name_check_attrs(
                                check_url=str(request.url_for("get_create_check_name")),
                                kind="tag",
                                target_id=name_feedback_id,
                                exclude_id=tag.id if tag else None,
                            ),
                        ),
                    ),
                    label(for_="md-editor-description")["Description"],
                    markdown_editor(
                        field_id="description",
                        name="description",
                        value=prefill.description if prefill else None,
                    ),
                    label(for_="category")["Category"],
                    select(name="category", id="category", class_="single-select")[
                        [
                            option(
                                value=cat.value,
                                selected=cat
                                == (
                                    prefill.category if prefill else TagCategory.general
                                ),
                                data_icon=CATEGORY_ICONS[cat],
                                data_color=CATEGORY_COLORS[cat],
                                data_category=cat.value,
                            )[titlecase(cat.value)]
                            for cat in TagCategory
                        ]
                    ],
                    label(for_="implication_ids")["Child of"],
                    select(
                        name="implication_ids",
                        id="implication_ids",
                        multiple=True,
                        class_="multi-select",
                        data_options_url=options_url,
                    )[
                        [
                            option(
                                value=t.id,
                                selected=True,
                                data_icon=CATEGORY_ICONS.get(t.category, "tag"),
                                data_color=CATEGORY_COLORS.get(t.category, ""),
                                data_category=t.category.value,
                            )["(P) " + t.name if t.is_pending else t.name]
                            for t in selected_implications
                        ]
                    ],
                    label(for_="aliases")["Aliases"],
                    select(
                        name="aliases",
                        id="aliases",
                        multiple=True,
                        class_="alias-select",
                    )[
                        [
                            option(value=alias, selected=True)[alias]
                            for alias in current_aliases
                        ]
                    ],
                    button(
                        type="submit",
                        id="tag-form-submit",
                        formnovalidate=True,
                        class_=(
                            "mt-2 px-4 py-2 rounded-lg bg-main hover:bg-main-hover "
                            "border border-lightest cursor-pointer text-base-text "
                            "w-full transition-opacity"
                        ),
                    )["Submit"],
                ],
            ]
        ),
        request=request,
    )
