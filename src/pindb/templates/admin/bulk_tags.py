import json
from typing import Any

from fastapi import Request
from htpy import Element, a, button, div, form, hr, i, input, p, pre, textarea

from pindb.templates.base import html_base
from pindb.templates.components.bread_crumb import bread_crumb
from pindb.templates.components.centered import centered_div
from pindb.templates.components.form_field import form_field
from pindb.templates.components.page_heading import page_heading


def bulk_tags_page(
    request: Request,
    *,
    error_message: str | None = None,
    result: dict[str, Any] | None = None,
) -> Element:

    return html_base(
        title="Bulk tags",
        request=request,
        body_content=centered_div(
            content=[
                bread_crumb(
                    entries=[
                        (request.url_for("get_admin_panel"), "Admin"),
                        "Bulk tags",
                    ]
                ),
                page_heading(icon="tags", text="Bulk tags"),
                p(class_="text-pin-base-300 text-sm max-w-2xl")[
                    'Paste JSON or upload a .json file. The payload must be either a single Tag or an object with a "tags" key: a list of tag trees (name, category, aliases, implications). '
                    "Existing tags are merged; new implications propagate to pins like the tag editor."
                ],
                hr,
                error_message
                and div(
                    class_="alert alert-error max-w-2xl text-sm whitespace-pre-wrap"
                )[error_message],
                (result is not None)
                and div(class_="alert alert-success max-w-2xl text-sm")[
                    p(class_="font-semibold")["Import completed."],
                    p["Root tag IDs: ", str(result.get("root_tag_ids", []))],
                    p["Touched tag IDs: ", str(result.get("touched_tag_ids", []))],
                    pre(
                        class_="mt-2 text-xs bg-pin-base-900/50 p-2 rounded overflow-x-auto"
                    )[json.dumps(result, indent=2, ensure_ascii=False)],
                ],
                form(
                    method="post",
                    action=str(request.url_for("post_admin_bulk_tags")),
                    enctype="multipart/form-data",
                    class_="flex flex-col gap-4 max-w-2xl",
                )[
                    form_field(
                        label_text="JSON",
                        field_id="bulk-tags-json",
                        child=textarea(
                            id="bulk-tags-json",
                            name="json_text",
                            rows=18,
                            class_="textarea textarea-bordered w-full font-mono text-sm",
                            placeholder='{\n  "tags": [\n    {\n      "name": "example",\n      "category": "species",\n      "aliases": [],\n      "implications": []\n    }\n  ]\n}',
                        ),
                    ),
                    form_field(
                        label_text="Or upload a JSON file",
                        field_id="bulk-tags-file",
                        child=input(
                            id="bulk-tags-file",
                            type="file",
                            name="file",
                            accept="application/json,.json",
                            class_="file-input file-input-bordered w-full",
                        ),
                    ),
                    button(type="submit", class_="btn btn-primary w-fit")[
                        i(data_lucide="upload", class_="inline-block w-4 h-4 mr-1"),
                        "Submit",
                    ],
                ],
                hr,
                a(
                    href=str(request.url_for("get_admin_panel")),
                    class_="btn btn-ghost w-fit",
                )[
                    i(data_lucide="arrow-left", class_="inline-block w-4 h-4 mr-1"),
                    "Back to Admin",
                ],
            ],
            flex=True,
            col=True,
        ),
    )
