"""htpy page builder: `templates/bulk/tag.py`.

Bulk tag creation form. Spreadsheet-style row entry with reactive chip-color
theming and cross-row implication search. Initial implementation renders a
stub shell; the JS-driven row table is loaded from ``bulk_tag.js``."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import Request
from htpy import (
    Element,
    button,
    div,
    h1,
    p,
    script,
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
from pindb.templates.components.tag_branding import CATEGORY_COLORS, CATEGORY_ICONS

with open(
    file=Path(__file__).parent.parent / "js/bulk_tag.js",
    mode="r",
    encoding="utf-8",
) as _js_file:
    _SCRIPT_CONTENT = _js_file.read()


def bulk_tag_page(
    submit_url: str,
    options_base_url: str,
    request: Request | None = None,
) -> Element:
    ref_data: dict[str, object] = {
        "submitUrl": submit_url,
        "optionsBaseUrl": options_base_url,
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

    return html_base(
        title="Bulk Create Tags",
        request=request,
        body_content=[
            script[Markup(f"window.BULK_TAG_REF = {json.dumps(ref_data)};")],
            div(class_="px-4 py-4 flex flex-col gap-2 h-full")[
                h1(class_="text-xl font-semibold")["Bulk Create Tags"],
                p(class_="text-sm text-muted")[
                    "Create many tags at once. Implications can reference "
                    "existing tags or other rows in this batch."
                ],
                div(class_="flex gap-2")[
                    button(
                        type="button",
                        id="bulk-tag-add-row",
                        class_="px-3 py-1 rounded bg-accent text-white",
                    )["+ Add row"],
                    button(
                        type="button",
                        id="bulk-tag-submit",
                        class_="px-3 py-1 rounded border border-accent text-accent",
                    )["Submit"],
                ],
                table(class_="bulk-tag-table w-full border-collapse text-sm")[
                    thead[
                        tr(class_="border-b border-lightest")[
                            th(class_="px-2 py-1 text-left", data_col_type="name")[
                                "Name *"
                            ],
                            th(class_="px-2 py-1 text-left", data_col_type="category")[
                                "Category"
                            ],
                            th(
                                class_="px-2 py-1 text-left",
                                data_col_type="implications",
                            )["Child of"],
                            th(class_="px-2 py-1 text-left", data_col_type="aliases")[
                                "Aliases"
                            ],
                            th(
                                class_="px-2 py-1 text-left",
                                data_col_type="description",
                            )["Description"],
                            th(class_="px-2 py-1 text-left")["Actions"],
                        ]
                    ],
                    tbody(id="bulk-tag-tbody"),
                ],
            ],
        ],
        script_content=_SCRIPT_CONTENT,
    )
