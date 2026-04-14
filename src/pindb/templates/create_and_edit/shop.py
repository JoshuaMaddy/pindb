import json
from pathlib import Path

from fastapi import Request
from fastapi.datastructures import URL
from htpy import Element, div, form, hr, input, label, span
from markupsafe import Markup

from pindb.database.shop import Shop
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div
from pindb.templates.components.markdown_editor import markdown_editor
from pindb.templates.components.page_heading import page_heading

with open(
    file=Path(__file__).parent.parent / "js/pin_creation.js",
    mode="r",
    encoding="utf-8",
) as js_file:
    SCRIPT_CONTENT: str = js_file.read()


def shop_form(
    post_url: URL | str,
    request: Request,
    shop: Shop | None = None,
) -> Element:
    shop_links: list[str] = [link.path for link in shop.links] if shop else []
    if not shop_links:
        shop_links = [""]

    links_json: str = json.dumps(shop_links)

    return html_base(
        title="Create Shop" if not shop else "Edit Shop",
        body_content=centered_div(
            content=[
                page_heading(
                    icon="store" if not shop else "pencil",
                    text="Create a Shop" if not shop else "Edit a Shop",
                ),
                hr,
                form(
                    hx_post=str(post_url),
                    class_="flex flex-col gap-2 [&_label]:font-semibold",
                )[
                    label(for_="name")["Name", span(class_="text-red-200 ml-0.5")["*"]],
                    input(
                        type="text",
                        name="name",
                        id="name",
                        required=True,
                        class_="grow",
                        value=shop.name if shop else None,
                    ),
                    label(for_="md-editor-description")["Description"],
                    markdown_editor(
                        field_id="description",
                        name="description",
                        value=shop.description if shop else None,
                    ),
                    div[
                        label(for_="links")["Links"],
                        Markup(f"""<div class="mt-2" x-data="{{ links: {links_json.replace('"', "'")} }}">
                            <template x-for="(link, index) in links" :key="index">
                                <div class="grid grid-cols-[1fr_min-content] gap-2 mb-2">
                                    <input
                                        type="text"
                                        name="links"
                                        x-model="links[index]"
                                        class="col-span-1">
                                    <button
                                        type="button"
                                        @click="links.splice(index, 1)"
                                        x-show="links.length > 1"
                                        class="remove-link-button">Remove</button>
                                </div>
                            </template>
                            <button
                                type="button"
                                @click="links.push('')"
                                id="add-link-button"
                                class="w-full mt-2">Add Link</button>
                        </div>"""),
                    ],
                    input(
                        type="submit",
                        value="Submit",
                        class_="mt-2",
                    ),
                ],
            ]
        ),
        script_content=SCRIPT_CONTENT,
        request=request,
    )
