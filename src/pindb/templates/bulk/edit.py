"""Bulk-edit form rendered from a PinSet / Artist / Shop / Tag / search source."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from fastapi import Request
from fastapi.datastructures import URL
from htpy import (
    Element,
    Fragment,
    VoidElement,
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
from titlecase import titlecase

from pindb.database.tag import Tag
from pindb.model_utils import MAGNITUDE_INPUT_PATTERN
from pindb.models.acquisition_type import AcquisitionType
from pindb.models.funding_type import FundingType
from pindb.routes.bulk._helpers import TagMode
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div
from pindb.templates.components.page_heading import page_heading

with open(
    file=Path(__file__).parent.parent / "js/pin_creation.js",
    mode="r",
    encoding="utf-8",
) as _js_file:
    _PIN_CREATION_SCRIPT: str = _js_file.read()


def bulk_edit_page(
    *,
    post_url: URL | str,
    source_label: str,
    source_description: str,
    pin_count: int,
    tags: Sequence[Tag],
    options_base_url: str,
    viewer_is_admin: bool,
    request: Request,
) -> Element:
    title = f"Bulk edit — {source_label}"
    return html_base(
        title=title,
        request=request,
        script_content=_PIN_CREATION_SCRIPT,
        body_content=centered_div(
            content=[
                script[
                    Markup(
                        f"window.PIN_FORM_REF = {json.dumps({'optionsBaseUrl': options_base_url})};"
                    )
                ],
                page_heading(icon="pencil-ruler", text=title),
                p(class_="text-lightest-hover")[source_description],
                _pin_count_banner(pin_count=pin_count),
                _pending_notice(viewer_is_admin=viewer_is_admin),
                hr,
                form(
                    method="post",
                    action=str(post_url),
                    class_="flex flex-col gap-6",
                    autocomplete="off",
                )[
                    _tag_section(tags=tags, request=request),
                    hr,
                    _scalar_section(),
                    hr,
                    input(
                        type="submit",
                        value=f"Apply to {pin_count} pin(s)",
                        disabled=pin_count == 0 or None,
                    ),
                ],
            ],
        ),
    )


def _pin_count_banner(pin_count: int) -> Element:
    tone = "bg-darker" if pin_count else "bg-error-dark border border-error-dark"
    return div(class_=f"rounded px-4 py-2 text-sm {tone}")[
        i(data_lucide="layers", class_="inline-block w-4 h-4 mr-1"),
        f"This change will affect {pin_count} pin(s).",
    ]


def _pending_notice(viewer_is_admin: bool) -> Element | str:
    if viewer_is_admin:
        return ""
    return div(
        class_="rounded bg-error-dark border border-error-dark text-error-main px-4 py-2 text-sm"
    )[
        i(data_lucide="clock", class_="inline-block w-4 h-4 mr-1"),
        "Each affected pin will receive a pending edit for admin approval.",
    ]


def _tag_section(
    *,
    tags: Sequence[Tag],
    request: Request,
) -> Fragment:
    preview_url = str(request.url_for("get_tag_implication_preview"))
    tag_options = [
        option(value=str(tag.id), data_category=tag.category.value)[
            ("(P) " + tag.display_name) if tag.is_pending else tag.display_name
        ]
        for tag in sorted(tags, key=lambda t: (t.category, t.name))
    ]
    modes = [
        (TagMode.add, "Add", "Union these tags with each pin's existing tags."),
        (
            TagMode.remove,
            "Remove",
            "Remove these tags from each pin (no-op if absent).",
        ),
        (
            TagMode.replace,
            "Replace",
            "Overwrite each pin's explicit tags with exactly these.",
        ),
    ]
    return fragment[
        h2["Tags"],
        div(class_="flex flex-col gap-2")[
            label(for_="tag_ids", class_="font-semibold")["Tags"],
            select(
                name="tag_ids",
                id="tag_ids",
                multiple=True,
                class_="multi-select",
                data_entity_type="tag",
                hx_get=preview_url,
                # Defensive: if this form ever uses hx_swap="none", inherited swap would drop preview HTML.
                hx_swap="innerHTML",
                hx_trigger="load, change",
                hx_include="[name='tag_ids']",
                hx_target="#implication-preview",
            )[tag_options],
            div(id="implication-preview"),
            div(class_="flex flex-col gap-1 mt-2")[
                label(class_="font-semibold")["Tag mode"],
                *[
                    label(class_="flex items-start gap-2 cursor-pointer")[
                        input(
                            type="radio",
                            name="tag_mode",
                            value=mode.value,
                            checked=(mode == TagMode.add) or None,
                        ),
                        div[
                            span(class_="font-medium")[label_text],
                            span(class_="block text-xs text-lightest-hover")[
                                description
                            ],
                        ],
                    ]
                    for mode, label_text, description in modes
                ],
            ],
        ],
    ]


def _scalar_section() -> Fragment:
    return fragment[
        h2["Fields"],
        p(class_="text-lightest-hover text-sm")[
            "Only fields with the checkbox ticked are updated. Unticked fields "
            "are left unchanged on every pin.",
        ],
        div(class_="flex flex-col gap-3")[
            _scalar_row(
                field="acquisition_type",
                label_text="Acquisition",
                widget=_enum_select(
                    name="acquisition_type_value",
                    values=[
                        (m.value, titlecase(m.value.replace("_", " ")))
                        for m in AcquisitionType
                    ],
                ),
            ),
            _scalar_row(
                field="funding_type",
                label_text="Funding type",
                widget=_enum_select(
                    name="funding_type_value",
                    values=[("", "— none —")]
                    + [
                        (m.value, titlecase(m.value.replace("_", " ")))
                        for m in FundingType
                    ],
                ),
            ),
            _scalar_row(
                field="limited_edition",
                label_text="Limited edition",
                widget=_enum_select(
                    name="limited_edition_value",
                    values=[("true", "Yes"), ("false", "No")],
                ),
            ),
            _scalar_row(
                field="number_produced",
                label_text="Number produced",
                widget=input(
                    type="number",
                    name="number_produced_value",
                    min=0,
                    step=1,
                ),
            ),
            _scalar_row(
                field="posts",
                label_text="Posts",
                widget=input(
                    type="number",
                    name="posts_value",
                    min=1,
                    step=1,
                ),
            ),
            _scalar_row(
                field="width",
                label_text="Width",
                widget=input(
                    type="text",
                    name="width_value",
                    autocomplete="off",
                    pattern=MAGNITUDE_INPUT_PATTERN,
                    placeholder="e.g. 40mm or 1.5in",
                ),
            ),
            _scalar_row(
                field="height",
                label_text="Height",
                widget=input(
                    type="text",
                    name="height_value",
                    autocomplete="off",
                    pattern=MAGNITUDE_INPUT_PATTERN,
                    placeholder="e.g. 40mm or 1.5in",
                ),
            ),
            _scalar_row(
                field="release_date",
                label_text="Release date",
                widget=input(type="date", name="release_date_value"),
            ),
            _scalar_row(
                field="end_date",
                label_text="End date",
                widget=input(type="date", name="end_date_value"),
            ),
        ],
    ]


def _scalar_row(
    *,
    field: str,
    label_text: str,
    widget: Element | VoidElement,
) -> Element:
    return div(
        class_=(
            "flex flex-col gap-2 md:grid md:grid-cols-[max-content_max-content_minmax(0,1fr)] "
            "md:items-center md:gap-2"
        ),
    )[
        div(class_="flex items-center gap-2 md:contents")[
            input(
                type="checkbox",
                name="apply_field",
                value=field,
                id=f"apply_{field}",
            ),
            label(
                for_=f"apply_{field}",
                class_="font-semibold max-md:whitespace-normal md:whitespace-nowrap",
            )[label_text],
        ],
        div(class_="min-w-0 w-full md:contents")[widget],
    ]


def _enum_select(
    *,
    name: str,
    values: list[tuple[str, str]],
) -> Element:
    return select(name=name, class_="single-select")[
        [option(value=value)[label_text] for value, label_text in values]
    ]
