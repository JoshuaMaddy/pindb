"""Shared htpy form for entities with name/description/links/aliases (Artist, Shop)."""

from __future__ import annotations

import json
from typing import Sequence

from fastapi import Request
from fastapi.datastructures import URL
from htpy import (
    Element,
    button,
    div,
    form,
    hr,
    input,
    label,
    option,
    script,
    select,
    span,
)
from markupsafe import Markup

from pindb.database.artist import Artist
from pindb.database.shop import Shop
from pindb.templates.base import html_base
from pindb.templates.components.forms.markdown_editor import markdown_editor
from pindb.templates.components.forms.name_availability import (
    name_availability_field,
    name_check_attrs,
)
from pindb.templates.components.layout.centered import centered_div
from pindb.templates.components.layout.page_heading import page_heading


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
    name_feedback_id: str = f"{entity_kind.lower()}-name-availability-feedback"
    heading_icon = create_icon if creating else "pencil"
    heading_text = (
        f"Create {create_article} {entity_kind}"
        if creating
        else f"Edit {create_article} {entity_kind}"
    )

    name_hint = f"Enter {create_article} {entity_kind.lower()} name."
    gate_cfg = {
        "formId": "simple-entity-form",
        "submitId": "simple-entity-submit",
        "fields": [
            {
                "key": "name",
                "kind": "text",
                "inputId": "name",
                "hint": name_hint,
                "highlightSelector": '[data-pin-field="name"]',
            }
        ],
    }
    gate_json = json.dumps(gate_cfg).replace("</", "<\\/")

    return html_base(
        title=title,
        template_js_extra=("forms/alias_select_init.js", "forms/entity_form_gate.js"),
        body_content=centered_div(
            content=[
                page_heading(icon=heading_icon, text=heading_text),
                hr,
                script(**{"type": "application/json"}, id="entity-form-gate-data")[
                    Markup(gate_json)
                ],
                form(
                    id="simple-entity-form",
                    hx_post=str(post_url),
                    hx_target="#pindb-toast-host",
                    hx_swap="innerHTML",
                    class_="flex flex-col gap-2 [&_label]:font-semibold",
                )[
                    label(for_="name")[
                        "Name", span(class_="text-error-main ml-0.5")["*"]
                    ],
                    name_availability_field(
                        feedback_id=name_feedback_id,
                        data_pin_field="name",
                        child=input(
                            type="text",
                            name="name",
                            id="name",
                            required=True,
                            autocomplete="off",
                            class_="grow",
                            value=entity.name if entity else None,
                            **name_check_attrs(
                                check_url=str(request.url_for("get_create_check_name")),
                                kind=entity_kind.lower(),
                                target_id=name_feedback_id,
                                exclude_id=entity.id if entity else None,
                            ),
                        ),
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
                    button(
                        type="submit",
                        id="simple-entity-submit",
                        formnovalidate=True,
                        class_=(
                            "mt-2 px-4 py-2 rounded-lg bg-main hover:bg-main-hover "
                            "border border-lightest cursor-pointer text-base-text "
                            "w-full transition-opacity"
                        ),
                    )["Submit"],
                ],
            ]
        ),
        request=request,
    )
