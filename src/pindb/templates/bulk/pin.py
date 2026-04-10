import json
from pathlib import Path
from typing import Sequence

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

from pindb.database import Artist, Material, PinSet, Shop, Tag
from pindb.database.currency import Currency
from pindb.models import AcquisitionType, FundingType
from pindb.templates.base import html_base

with open(
    file=Path(__file__).parent.parent / "js/bulk_import.js",
    mode="r",
    encoding="utf-8",
) as _js_file:
    _SCRIPT_CONTENT = _js_file.read()


def bulk_pin_page(
    upload_image_url: str,
    submit_url: str,
    shops: Sequence[Shop],
    materials: Sequence[Material],
    tags: Sequence[Tag],
    pin_sets: Sequence[PinSet],
    artists: Sequence[Artist],
    currencies: Sequence[Currency],
    request: Request | None = None,
) -> Element:
    ref_data: dict[
        str, str | list[dict[str, str]] | list[dict[str, int | str]] | int
    ] = {
        "uploadImageUrl": upload_image_url,
        "submitUrl": submit_url,
        "shops": [{"value": s.name, "text": s.name} for s in shops],
        "materials": [{"value": m.name, "text": m.name} for m in materials],
        "tags": [{"value": t.name, "text": t.name} for t in tags],
        "pinSets": [{"value": p.name, "text": p.name} for p in pin_sets],
        "artists": [{"value": a.name, "text": a.name} for a in artists],
        "currencies": [{"value": c.id, "text": c.code} for c in currencies],
        "acquisitionTypes": [
            {"value": a, "text": a.replace("_", " ").title()} for a in AcquisitionType
        ],
        "fundingTypes": [
            {"value": f, "text": f.replace("_", " ").title()} for f in FundingType
        ],
        "defaultCurrencyId": 840,
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

    return html_base(
        title="Bulk Import Pins",
        request=request,
        body_content=[
            # Inject reference data
            script[Markup(f"window.BULK_REF = {json.dumps(ref_data)};")],
            # Page wrapper — full width with padding
            div(class_="px-4 py-4 flex flex-col gap-2 h-full")[
                # Header bar
                div(class_="flex items-center gap-2 flex-wrap")[
                    h1(class_="grow")["Bulk Import Pins"],
                    # Columns toggle (Alpine dropdown)
                    Markup(f"""<div class="relative" x-data="{{open: false}}">
                        <button type="button" @click="open = !open" class="flex items-center gap-1">
                            <i data-lucide="columns-3"></i> Columns
                        </button>
                        <div x-show="open" @click.outside="open = false"
                             class="absolute right-0 top-full mt-1 z-50 bg-pin-main border border-pin-border rounded-lg p-3 flex flex-col gap-2 min-w-[160px]">
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
                    )[Markup('<i data-lucide="plus"></i>'), " Add Row"],
                    button(
                        id="submit-btn",
                        type="button",
                        class_="flex items-center gap-1 border-accent text-accent",
                    )[
                        Markup('<i data-lucide="upload"></i>'),
                        span(id="submit-label")["Submit (0)"],
                    ],
                ],
                hr,
                # Scrollable table container
                div(
                    class_="overflow-x-auto overflow-y-clip rounded-lg border border-pin-border"
                )[
                    table(class_="bulk-table w-full border-collapse text-sm")[
                        thead[
                            tr(class_="border-b border-pin-border")[
                                th(class_="bulk-th w-8")[
                                    Markup(
                                        '<input type="checkbox" id="select-all-rows">'
                                    )
                                ],
                                th(class_="bulk-th w-20")["Front *"],
                                th(class_="bulk-th w-20")["Back"],
                                th(
                                    class_="bulk-th min-w-[160px]", data_col_type="name"
                                )["Name *"],
                                th(
                                    class_="bulk-th min-w-[180px]",
                                    data_col_type="shops",
                                )["Shops *"],
                                th(
                                    class_="bulk-th min-w-[140px]",
                                    data_col_type="acquisition_type",
                                )["Acquisition *"],
                                th(
                                    class_="bulk-th min-w-[100px]",
                                    data_col_type="grades",
                                )["Grades *"],
                                th(
                                    class_="bulk-th min-w-[120px]",
                                    data_col_type="currency_id",
                                )["Currency *"],
                                th(
                                    class_="bulk-th min-w-[160px]",
                                    data_col_type="materials",
                                )["Materials *"],
                                th(
                                    class_="bulk-th min-w-[160px]", data_col_type="tags"
                                )["Tags *"],
                                # Optional columns
                                th(
                                    class_="bulk-th min-w-[160px]",
                                    data_col="artists",
                                    data_col_type="artists",
                                )["Artists"],
                                th(
                                    class_="bulk-th min-w-[160px]",
                                    data_col="pin_sets",
                                    data_col_type="pin_sets",
                                )["Pin Sets"],
                                th(
                                    class_="bulk-th min-w-[80px]",
                                    data_col="limited_edition",
                                )["Ltd. Ed."],
                                th(
                                    class_="bulk-th min-w-[100px]",
                                    data_col="number_produced",
                                    data_col_type="number_produced",
                                )["# Produced"],
                                th(
                                    class_="bulk-th min-w-[130px]",
                                    data_col="release_date",
                                    data_col_type="release_date",
                                )["Release Date"],
                                th(
                                    class_="bulk-th min-w-[130px]",
                                    data_col="end_date",
                                    data_col_type="end_date",
                                )["End Date"],
                                th(
                                    class_="bulk-th min-w-[130px]",
                                    data_col="funding_type",
                                    data_col_type="funding_type",
                                )["Funding"],
                                th(
                                    class_="bulk-th min-w-[70px]",
                                    data_col="posts",
                                    data_col_type="posts",
                                )["Posts"],
                                th(
                                    class_="bulk-th min-w-[90px]",
                                    data_col="width",
                                    data_col_type="width",
                                )["Width"],
                                th(
                                    class_="bulk-th min-w-[90px]",
                                    data_col="height",
                                    data_col_type="height",
                                )["Height"],
                                th(class_="bulk-th min-w-[100px]", data_col="links")[
                                    "Links"
                                ],
                                th(
                                    class_="bulk-th min-w-[180px]",
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
            # Success modal (hidden until submit succeeds)
            div(
                id="success-modal",
                class_="hidden fixed inset-0 z-50 flex items-center justify-center bg-black/60",
            )[
                div(
                    class_="bg-pin-main border border-pin-border rounded-xl p-6 max-w-2xl w-full max-h-[80vh] flex flex-col gap-4"
                )[
                    div(class_="flex items-center justify-between")[
                        h1(id="modal-title", class_="text-xl font-bold")[
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
        script_content=_SCRIPT_CONTENT,
    )
