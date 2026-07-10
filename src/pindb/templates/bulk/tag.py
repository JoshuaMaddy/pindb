"""htpy page builder: `templates/bulk/tag.py`.

Bulk tag creation form. Spreadsheet-style row entry with reactive chip-color
theming and cross-row implication search — rendered by the ``bulk-tag``
Svelte island."""

from __future__ import annotations

from fastapi import Request
from htpy import Element
from titlecase import titlecase

from pindb.database.tag import TagCategory
from pindb.templates.base import html_base
from pindb.templates.components.islands import island
from pindb.templates.components.tags.tag_branding import CATEGORY_COLORS, CATEGORY_ICONS


def bulk_tag_page(
    submit_url: str,
    options_base_url: str,
    request: Request | None = None,
) -> Element:
    island_props: dict[str, object] = {
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

    return html_base(
        title="Bulk Create Tags",
        request=request,
        body_content=[
            island("bulk-tag", props=island_props),
        ],
    )
