"""Shared htpy form for entities with name/description/links/aliases (Artist, Shop)."""

from __future__ import annotations

import json
from typing import Sequence

from fastapi import Request
from fastapi.datastructures import URL
from htpy import Element, div, form, hr, input, label, option, select, span
from markupsafe import Markup

from pindb.database.artist import Artist
from pindb.database.shop import Shop
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div
from pindb.templates.components.markdown_editor import markdown_editor
from pindb.templates.components.page_heading import page_heading

_ALIAS_SCRIPT = """
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll("select.alias-select").forEach(function(el) {
        new TomSelect(el, {
            maxItems: null,
            create: true,
            persist: false,
            plugins: ["remove_button"],
        });
    });
});
"""


def simple_aliased_entity_form(
    *,
    post_url: URL | str,
    request: Request,
    entity: Artist | Shop | None,
    entity_kind: str,
    create_icon: str,
    create_article: str,
) -> Element:
    """Shared scaffold; ``entity_kind`` capitalized (``"Artist"``/``"Shop"``)."""
    current_aliases: Sequence[str] = [a.alias for a in entity.aliases] if entity else []
    entity_links: list[str] = [link.path for link in entity.links] if entity else []
    if not entity_links:
        entity_links = [""]

    links_json: str = json.dumps(entity_links)

    creating = entity is None
    title = f"Create {entity_kind}" if creating else f"Edit {entity_kind}"
    heading_icon = create_icon if creating else "pencil"
    heading_text = (
        f"Create {create_article} {entity_kind}"
        if creating
        else f"Edit {create_article} {entity_kind}"
    )

    return html_base(
        title=title,
        body_content=centered_div(
            content=[
                page_heading(icon=heading_icon, text=heading_text),
                hr,
                form(
                    hx_post=str(post_url),
                    hx_target="#pindb-toast-host",
                    hx_swap="innerHTML",
                    class_="flex flex-col gap-2 [&_label]:font-semibold",
                )[
                    label(for_="name")[
                        "Name", span(class_="text-error-main ml-0.5")["*"]
                    ],
                    input(
                        type="text",
                        name="name",
                        id="name",
                        required=True,
                        autocomplete="off",
                        class_="grow",
                        value=entity.name if entity else None,
                    ),
                    label(for_="md-editor-description")["Description"],
                    markdown_editor(
                        field_id="description",
                        name="description",
                        value=entity.description if entity else None,
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
