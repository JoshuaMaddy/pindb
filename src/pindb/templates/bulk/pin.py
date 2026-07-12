"""
htpy page and fragment builders: `templates/bulk/pin.py`.
"""

from typing import Sequence

from fastapi import Request
from htpy import Element, div, p, script

from pindb.asset_cache_buster import STATIC_CACHE_BUSTER
from pindb.database.currency import Currency
from pindb.model_utils import MAGNITUDE_INPUT_PATTERN
from pindb.models import AcquisitionType, FundingType
from pindb.templates.base import html_base
from pindb.templates.components.islands import island
from pindb.utils import pretty_titlecase

_OPTIONAL_COLS: list[tuple[str, str]] = [
    ("artists", "Artists"),
    ("pin_sets", "Pin Sets"),
    ("limited_edition", "Ltd. Ed."),
    ("number_produced", "# Produced"),
    ("release_date", "Release Date"),
    ("end_date", "End Date"),
    ("funding_type", "Funding"),
    ("posts", "Posts"),
    ("width", "Width"),
    ("height", "Height"),
    ("links", "Links"),
    ("description", "Description"),
]


def bulk_pin_page(
    upload_image_url: str,
    submit_url: str,
    options_base_url: str,
    currencies: Sequence[Currency],
    request: Request | None = None,
) -> Element:
    island_props: dict[str, object] = {
        "uploadImageUrl": upload_image_url,
        "submitUrl": submit_url,
        "optionsBaseUrl": options_base_url,
        "nameCheckUrl": (
            str(request.url_for("get_create_check_name")) if request is not None else ""
        ),
        "currencies": [{"value": c.id, "text": c.code} for c in currencies],
        "acquisitionTypes": [
            {"value": a, "text": pretty_titlecase(a.replace("_", " "))}
            for a in AcquisitionType
        ],
        "fundingTypes": [
            {"value": f, "text": pretty_titlecase(f.replace("_", " "))}
            for f in FundingType
        ],
        "defaultCurrencyId": 999,
        "magnitudeInputPattern": MAGNITUDE_INPUT_PATTERN,
        "optionalCols": [{"key": key, "label": label} for key, label in _OPTIONAL_COLS],
    }

    return html_base(
        title="Bulk Import Pins",
        request=request,
        head_content=script(
            **{"type": "module"},
            src=f"/static/vendor/pindb-webp/pindb-webp-encode.js?v={STATIC_CACHE_BUSTER}",
        ),
        template_js_extra=("shared/webp_transcode.js",),
        body_content=[
            div(class_="px-4 py-4 flex flex-col gap-2 h-full")[
                div(
                    class_="md:hidden rounded-lg border border-error-dark bg-error-dark px-3 py-2 text-sm text-error-main-hover"
                )[
                    p(class_="font-semibold")["Not available on small screens."],
                    p(class_="mt-1 text-error-main")[
                        "Bulk pin import needs a wider layout. Resize the window or use a tablet or desktop to add rows and submit."
                    ],
                ],
                # Header bar + grid + success modal all live in the island.
                island(
                    "bulk-import",
                    props=island_props,
                    class_=(
                        "max-md:pointer-events-none max-md:cursor-not-allowed "
                        "max-md:select-none max-md:opacity-60 flex flex-col gap-2"
                    ),
                ),
            ],
        ],
    )
