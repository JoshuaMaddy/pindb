"""
htpy page and fragment builders: `templates/components/pagination_controls.py`.
"""

import math
from urllib.parse import urlencode

from htpy import Element, a, div, span


def pagination_controls(
    base_url: str,
    page: int,
    total_count: int,
    section_id: str,
    per_page: int = 100,
    extra_params: dict[str, str] | None = None,
) -> Element | None:
    total_pages: int = math.ceil(total_count / per_page) if total_count else 1
    if total_pages <= 1:
        return None

    def _nav_link(
        label: str,
        aria_label: str,
        target_page: int,
        enabled: bool,
    ) -> Element:
        if not enabled:
            return span(
                class_="opacity-40 cursor-not-allowed px-2 py-1", aria_hidden="true"
            )[label]
        params: dict[str, str] = {"page": str(target_page)}
        if extra_params:
            params.update(extra_params)
        href: str = f"{base_url}?{urlencode(params)}"
        return a(
            href=href,
            aria_label=aria_label,
            hx_get=href,
            hx_target=f"#{section_id}",
            hx_swap="outerHTML",
            hx_push_url="true",
            class_="px-2 py-1 rounded border border-pin-base-400 hover:border-accent",
        )[label]

    return div(class_="flex items-center gap-2 text-sm mt-4")[
        _nav_link(
            label="← Prev",
            aria_label="Previous page",
            target_page=page - 1,
            enabled=page > 1,
        ),
        span(class_="text-pin-base-400")[f"Page {page} of {total_pages}"],
        _nav_link(
            label="Next →",
            aria_label="Next page",
            target_page=page + 1,
            enabled=page < total_pages,
        ),
    ]
