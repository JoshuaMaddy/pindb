"""
htpy page and fragment builders: `templates/create_and_edit/artist.py`.
"""

import json

from fastapi import Request
from fastapi.datastructures import URL
from htpy import Element, div, form, hr, input, label, option, select, span
from markupsafe import Markup

from pindb.database.artist import Artist
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div
from pindb.templates.components.markdown_editor import markdown_editor
from pindb.templates.components.page_heading import page_heading

_ALIAS_SCRIPT = """
document.querySelectorAll("select.alias-select").forEach(function(el) {
    new TomSelect(el, {
        maxItems: null,
        create: true,
        persist: false,
        plugins: ["remove_button"],
    });
});
"""


def artist_form(
    post_url: URL | str,
    request: Request,
    artist: Artist | None = None,
) -> Element:
    current_aliases: list[str] = [a.alias for a in artist.aliases] if artist else []
    artist_links: list[str] = [link.path for link in artist.links] if artist else []
    if not artist_links:
        artist_links = [""]

    links_json: str = json.dumps(artist_links)

    return html_base(
        title="Create Artist" if not artist else "Edit Artist",
        body_content=centered_div(
            content=[
                page_heading(
                    icon="palette" if not artist else "pencil",
                    text="Create an Artist" if not artist else "Edit an Artist",
                ),
                hr,
                form(
                    hx_post=str(post_url),
                    hx_target="#pindb-toast-host",
                    hx_swap="innerHTML",
                    class_="flex flex-col gap-2 [&_label]:font-semibold",
                )[
                    label(for_="name")["Name", span(class_="text-red-200 ml-0.5")["*"]],
                    input(
                        type="text",
                        name="name",
                        id="name",
                        required=True,
                        autocomplete="off",
                        class_="grow",
                        value=artist.name if artist else None,
                    ),
                    label(for_="md-editor-description")["Description"],
                    markdown_editor(
                        field_id="description",
                        name="description",
                        value=artist.description if artist else None,
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
                                        autocomplete="off"
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
                                class="w-full mt-2">Add Another Link</button>
                        </div>"""),
                    ],
                    label(for_="aliases")["Aliases"],
                    select(
                        name="aliases",
                        id="aliases",
                        multiple=True,
                        class_="alias-select",
                    )[
                        [
                            option(value=alias, selected=True)[alias]
                            for alias in current_aliases
                        ]
                    ],
                    input(
                        type="submit",
                        value="Submit",
                        class_="mt-2",
                    ),
                ],
            ]
        ),
        script_content=Markup(_ALIAS_SCRIPT),
        request=request,
    )
