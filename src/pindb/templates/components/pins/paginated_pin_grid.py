"""
htpy page and fragment builders: `templates/components/pins/paginated_pin_grid.py`.
"""

from typing import Sequence

from fastapi import Request
from htpy import Element, br, div, h2

from pindb.database.pin import Pin
from pindb.templates.components.listing.pagination_controls import pagination_controls
from pindb.templates.components.pins.pin_grid import pin_grid

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
        pagination_controls(
            base_url=page_url,
            page=page,
            total_count=total_count,
            section_id=_SECTION_ID,
            per_page=per_page,
        ),
    ]
