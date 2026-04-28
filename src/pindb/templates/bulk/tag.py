"""htpy page builder: `templates/bulk/tag.py`.

Bulk tag creation form. Spreadsheet-style row entry with reactive chip-color
theming and cross-row implication search. Initial implementation renders a
stub shell; the JS-driven row table is loaded from ``bulk_tag.js``."""

from __future__ import annotations

import json

from fastapi import Request
from htpy import (
    Element,
    button,
    div,
    h1,
    hr,
    script,
    span,
    table,
    tbody,
    th,
    thead,
    tr,
)
from markupsafe import Markup
from titlecase import titlecase

from pindb.database.tag import TagCategory
from pindb.templates.base import html_base
from pindb.templates.components.tags.tag_branding import CATEGORY_COLORS, CATEGORY_ICONS


def bulk_tag_page(
    submit_url: str,
    options_base_url: str,
    request: Request | None = None,
) -> Element:
    ref_data: dict[str, object] = {
        "submitUrl": submit_url,
        "optionsBaseUrl": options_base_url,
        "nameCheckUrl": (
            str(request.url_for("get_create_check_name")) if request is not None else ""
        ),
        "categories": [
            {
                "value": cat.value,
                "text": titlecase(cat.value),
                "color": CATEGORY_COLORS[cat],
                "icon": CATEGORY_ICONS[cat],
            }
            for cat in TagCategory
        ],
    }
    ref_json = json.dumps(ref_data).replace("</", "<\\/")

    return html_base(
        title="Bulk Create Tags",
        request=request,
        template_js_extra=("bulk/bulk_tag.js",),
        body_content=[
            script(**{"type": "application/json"}, id="bulk-tag-ref-data")[
                Markup(ref_json)
            ],
            div(class_="px-4 py-4 flex flex-col gap-2 h-full")[
                div(class_="flex items-center gap-2 flex-wrap")[
                    h1(class_="grow")["Bulk Create Tags"],
                    button(
                        type="button",
                        id="bulk-tag-add-row",
                        class_="flex items-center gap-1",
                    )[
                        Markup('<i data-lucide="plus" aria-hidden="true"></i>'),
                        " Add Row",
                    ],
                    button(
                        type="button",
                        id="bulk-tag-submit",
                        class_="flex items-center gap-1 border-accent text-accent",
                    )[
                        Markup('<i data-lucide="upload" aria-hidden="true"></i>'),
                        span(id="bulk-tag-submit-label")["Submit"],
                    ],
                ],
                hr,
                div(
                    class_="overflow-x-auto overflow-y-clip rounded-lg border border-lightest"
                )[
                    table(class_="bulk-tag-table w-full border-collapse text-sm")[
                        thead[
                            tr(class_="border-b border-lightest")[
                                th(class_="bulk-th", data_col_type="name")["Name *"],
                                th(class_="bulk-th", data_col_type="category")[
                                    "Category"
                                ],
                                th(class_="bulk-th", data_col_type="implications")[
                                    "Child of"
                                ],
                                th(class_="bulk-th", data_col_type="aliases")[
                                    "Aliases"
                                ],
                                th(
                                    class_="bulk-th min-w-20",
                                    data_col_type="description",
                                )["Description"],
                                th(class_="bulk-th")["Actions"],
                            ]
                        ],
                        tbody(id="bulk-tag-tbody"),
                    ],
                ],
            ],
            div(
                id="bulk-tag-success-modal",
                class_="hidden fixed inset-0 z-50 flex items-center justify-center bg-darker/80",
            )[
                div(
                    class_="bg-main border border-lightest rounded-xl p-6 max-w-2xl w-full max-h-[80vh] flex flex-col gap-4"
                )[
                    div(class_="flex items-center justify-between")[
                        h1(
                            id="bulk-tag-modal-title",
                            class_="text-lg font-bold sm:text-xl",
                        )["Tag Creation Complete"],
                        button(
                            id="bulk-tag-modal-close-btn",
                            type="button",
                            class_="hover:text-accent",
                        )[Markup('<i data-lucide="x"></i>')],
                    ],
                    div(
                        id="bulk-tag-modal-grid",
                        class_="grid grid-cols-[repeat(auto-fill,minmax(120px,1fr))] gap-2 overflow-y-auto",
                    ),
                ]
            ],
        ],
    )
