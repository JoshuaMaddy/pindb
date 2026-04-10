import math
from typing import Sequence

from fastapi import Request
from htpy import Element, a, br, div, h2, span

from pindb.database.pin import Pin
from pindb.templates.components.pin_grid import pin_grid

_SECTION_ID: str = "pins-section"


def paginated_pin_grid(
    request: Request,
    pins: Sequence[Pin],
    total_count: int,
    page: int,
    page_url: str,
    per_page: int = 100,
) -> Element:
    return div(id=_SECTION_ID)[
        bool(total_count) and h2[f"All Pins ({total_count})"],
        br,
        pin_grid(request=request, pins=pins),
        _pagination_controls(
            page_url=page_url,
            page=page,
            total_count=total_count,
            per_page=per_page,
        ),
    ]


def _pagination_controls(
    page_url: str,
    page: int,
    total_count: int,
    per_page: int,
) -> Element | None:
    total_pages: int = math.ceil(total_count / per_page) if total_count else 1
    if total_pages <= 1:
        return None

    def _nav_link(label: str, target_page: int, enabled: bool) -> Element:
        if not enabled:
            return span(class_="opacity-40 cursor-not-allowed px-3 py-1")[label]
        href: str = f"{page_url}?page={target_page}"
        return a(
            href=href,
            hx_get=href,
            hx_target=f"#{_SECTION_ID}",
            hx_swap="outerHTML",
            hx_push_url="true",
            class_="px-3 py-1 rounded border border-pin-base-400 hover:border-accent",
        )[label]

    return div(class_="flex items-center gap-3 text-sm mt-4")[
        _nav_link(label="← Prev", target_page=page - 1, enabled=page > 1),
        span(class_="text-pin-base-400")[f"Page {page} of {total_pages}"],
        _nav_link(label="Next →", target_page=page + 1, enabled=page < total_pages),
    ]
