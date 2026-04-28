"""
htpy page and fragment builders: `templates/bulk/pin.py`.
"""

import json
from typing import Sequence

from fastapi import Request
from htpy import (
    Element,
    button,
    div,
    h1,
    hr,
    p,
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

from pindb.database.currency import Currency
from pindb.model_utils import MAGNITUDE_INPUT_PATTERN
from pindb.models import AcquisitionType, FundingType
from pindb.templates.base import html_base


def bulk_pin_page(
    upload_image_url: str,
    submit_url: str,
    options_base_url: str,
    currencies: Sequence[Currency],
    request: Request | None = None,
) -> Element:
    ref_data: dict[
        str, str | list[dict[str, str]] | list[dict[str, int | str]] | int
    ] = {
        "uploadImageUrl": upload_image_url,
        "submitUrl": submit_url,
        "optionsBaseUrl": options_base_url,
        "nameCheckUrl": (
            str(request.url_for("get_create_check_name")) if request is not None else ""
        ),
        "currencies": [{"value": c.id, "text": c.code} for c in currencies],
        "acquisitionTypes": [
            {"value": a, "text": titlecase(a.replace("_", " "))}
            for a in AcquisitionType
        ],
        "fundingTypes": [
            {"value": f, "text": titlecase(f.replace("_", " "))} for f in FundingType
        ],
        "defaultCurrencyId": 999,
        "magnitudeInputPattern": MAGNITUDE_INPUT_PATTERN,
    }

    optional_cols: list[tuple[str, str]] = [
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
    ref_json = json.dumps(ref_data).replace("</", "<\\/")

    return html_base(
        title="Bulk Import Pins",
        request=request,
        template_js_extra=("bulk/bulk_import.js",),
        body_content=[
            script(**{"type": "application/json"}, id="bulk-ref-data")[
                Markup(ref_json)
            ],
            # Page wrapper — full width with padding
            div(class_="px-4 py-4 flex flex-col gap-2 h-full")[
                div(
                    class_="md:hidden rounded-lg border border-error-dark bg-error-dark px-3 py-2 text-sm text-error-main-hover"
                )[
                    p(class_="font-semibold")["Not available on small screens."],
                    p(class_="mt-1 text-error-main")[
                        "Bulk pin import needs a wider layout. Resize the window or use a tablet or desktop to add rows and submit."
                    ],
                ],
                # Header bar + table (disabled below md — wide table layout)
                div(
                    class_="max-md:pointer-events-none max-md:cursor-not-allowed max-md:select-none max-md:opacity-60 flex flex-col gap-2"
                )[
                    # Header bar
                    div(class_="flex items-center gap-2 flex-wrap")[
                        h1(class_="grow")["Bulk Import Pins"],
                        # Columns toggle (Alpine dropdown)
                        Markup(f"""<div class="relative" x-data="{{open: false}}">
                        <button type="button" @click="open = !open" class="flex items-center gap-1">
                            <i data-lucide="columns-3" aria-hidden="true"></i> Columns
                        </button>
                        <div x-show="open" @click.outside="open = false"
                             class="absolute right-0 top-full mt-1 z-50 bg-main border border-lightest rounded-lg p-3 flex flex-col gap-2 min-w-40">
                            {
                            "".join(
                                f'<label class="flex items-center gap-2 cursor-pointer font-semibold">'
                                f'<input type="checkbox" checked data-col="{key}" class="col-toggle-check"> {label}</label>'
                                for key, label in optional_cols
                            )
                        }
                        </div>
                    </div>"""),
                        button(
                            id="add-row-btn",
                            type="button",
                            class_="flex items-center gap-1",
                        )[
                            Markup('<i data-lucide="plus" aria-hidden="true"></i>'),
                            " Add Row",
                        ],
                        button(
                            id="submit-btn",
                            type="button",
                            class_="flex items-center gap-1 border-accent text-accent",
                        )[
                            Markup('<i data-lucide="upload" aria-hidden="true"></i>'),
                            span(id="submit-label")["Submit (0)"],
                        ],
                    ],
                    hr,
                    # Scrollable table container
                    div(
                        class_="overflow-x-auto overflow-y-clip rounded-lg border border-lightest"
                    )[
                        table(class_="bulk-table w-full border-collapse text-sm")[
                            thead[
                                tr(class_="border-b border-lightest")[
                                    th(
                                        class_="bulk-th bulk-sticky-left bulk-sticky-col-0 w-8"
                                    )[
                                        Markup(
                                            '<input type="checkbox" id="select-all-rows" aria-label="Select all rows">'
                                        )
                                    ],
                                    th(
                                        class_="bulk-th bulk-sticky-left bulk-sticky-col-1 w-22"
                                    )["Front *"],
                                    th(class_="bulk-th w-22")["Back"],
                                    th(
                                        class_="bulk-th bulk-sticky-left bulk-sticky-col-2 min-w-[15ch]",
                                        data_col_type="name",
                                    )["Name *"],
                                    th(
                                        class_="bulk-th min-w-45",
                                        data_col_type="shops",
                                    )["Shops *"],
                                    th(
                                        class_="bulk-th min-w-35",
                                        data_col_type="acquisition_type",
                                    )["Acquisition *"],
                                    th(
                                        class_="bulk-th min-w-25",
                                        data_col_type="grades",
                                    )["Grades *"],
                                    th(
                                        class_="bulk-th min-w-30",
                                        data_col_type="currency_id",
                                    )["Currency *"],
                                    th(
                                        class_="bulk-th min-w-[320px]",
                                        data_col_type="tags",
                                    )["Tags *"],
                                    # Optional columns
                                    th(
                                        class_="bulk-th min-w-40",
                                        data_col="artists",
                                        data_col_type="artists",
                                    )["Artists"],
                                    th(
                                        class_="bulk-th min-w-40",
                                        data_col="pin_sets",
                                        data_col_type="pin_sets",
                                    )["Pin Sets"],
                                    th(
                                        class_="bulk-th min-w-20",
                                        data_col="limited_edition",
                                    )["Ltd. Ed."],
                                    th(
                                        class_="bulk-th min-w-25",
                                        data_col="number_produced",
                                        data_col_type="number_produced",
                                    )["# Produced"],
                                    th(
                                        class_="bulk-th min-w-32.5",
                                        data_col="release_date",
                                        data_col_type="release_date",
                                    )["Release Date"],
                                    th(
                                        class_="bulk-th min-w-32.5",
                                        data_col="end_date",
                                        data_col_type="end_date",
                                    )["End Date"],
                                    th(
                                        class_="bulk-th min-w-32.5",
                                        data_col="funding_type",
                                        data_col_type="funding_type",
                                    )["Funding"],
                                    th(
                                        class_="bulk-th min-w-17.5",
                                        data_col="posts",
                                        data_col_type="posts",
                                    )["Posts"],
                                    th(
                                        class_="bulk-th min-w-22.5",
                                        data_col="width",
                                        data_col_type="width",
                                    )["Width"],
                                    th(
                                        class_="bulk-th min-w-22.5",
                                        data_col="height",
                                        data_col_type="height",
                                    )["Height"],
                                    th(class_="bulk-th min-w-25", data_col="links")[
                                        "Links"
                                    ],
                                    th(
                                        class_="bulk-th min-w-45",
                                        data_col="description",
                                        data_col_type="description",
                                    )["Description"],
                                    th(class_="bulk-th w-20")["Actions"],
                                ]
                            ],
                            tbody(id="bulk-tbody"),
                        ]
                    ],
                    # Results panel (hidden until submit)
                    div(id="results-panel", class_="hidden"),
                ],
            ],
            # Success modal (hidden until submit succeeds)
            div(
                id="success-modal",
                class_="hidden fixed inset-0 z-50 flex items-center justify-center bg-darker/80",
            )[
                div(
                    class_="bg-main border border-lightest rounded-xl p-6 max-w-2xl w-full max-h-[80vh] flex flex-col gap-4"
                )[
                    div(class_="flex items-center justify-between")[
                        h1(id="modal-title", class_="text-lg font-bold sm:text-xl")[
                            "Import Complete"
                        ],
                        button(
                            id="modal-close-btn",
                            type="button",
                            class_="hover:text-accent",
                        )[Markup('<i data-lucide="x"></i>')],
                    ],
                    div(
                        id="modal-grid",
                        class_="grid grid-cols-[repeat(auto-fill,minmax(120px,1fr))] gap-2 overflow-y-auto",
                    ),
                ]
            ],
        ],
    )
