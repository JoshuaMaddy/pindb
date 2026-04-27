"""
htpy page and fragment builders: `templates/create_and_edit/tag.py`.
"""

from fastapi import Request
from fastapi.datastructures import URL
from htpy import Element, div, form, hr, i, input, label, option, select, span
from markupsafe import Markup
from titlecase import titlecase

from pindb.database.tag import Tag, TagCategory
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div
from pindb.templates.components.markdown_editor import markdown_editor
from pindb.templates.components.page_heading import page_heading
from pindb.templates.components.tag_branding import CATEGORY_COLORS, CATEGORY_ICONS

_INIT_SCRIPT = """
document.addEventListener('DOMContentLoaded', function() {
    var _tagRender = { option: TagSelect.tagOptionRender, item: TagSelect.tagItemRender };
    var _noResults = {
        no_results: function(data) {
            var msg = data.input && data.input.length > 0 ? "No results found" : "Start typing to search\u2026";
            return '<div class="no-results">' + msg + '</div>';
        }
    };

    document.querySelectorAll("select.multi-select").forEach(function(el) {
        var optionsUrl = el.dataset.optionsUrl;
        new TomSelect(el, Object.assign({
            load: function(query, callback) {
                var sep = optionsUrl.includes('?') ? '&' : '?';
                fetch(optionsUrl + sep + 'q=' + encodeURIComponent(query))
                    .then(function(r) { return r.json(); })
                    .then(callback)
                    .catch(function() { callback(); });
            },
            shouldLoad: function(q) { return q.length > 0; },
            maxItems: null,
            valueField: "value",
            labelField: "text",
            persist: true,
            plugins: ["caret_position", "remove_button"],
            render: Object.assign({}, _noResults, _tagRender)
        }, TagSelect.tagSelectLucideCallbacks()));
    });

    document.querySelectorAll("select.single-select").forEach(function(el) {
        new TomSelect(el, Object.assign({
            render: _tagRender
        }, TagSelect.tagSingleSelectCallbacks()));
    });

    document.querySelectorAll("select.alias-select").forEach(function(el) {
        new TomSelect(el, {
            maxItems: null,
            create: true,
            persist: false,
            plugins: ["remove_button"],
            onInitialize: function() { this.addItems([]); }
        });
    });
});
"""


def _duplicate_notice(source_display_name: str) -> Element:
    return div(
        class_="rounded bg-blue-900 border border-blue-600 text-blue-200 px-4 py-2 text-sm my-2"
    )[
        i(data_lucide="copy", class_="inline-block w-4 h-4 mr-1"),
        f'Duplicating "{source_display_name}". Fields are prefilled — change the name if needed and submit to create the new tag.',
    ]


def tag_form(
    post_url: URL | str,
    request: Request,
    options_url: str,
    tag: Tag | None = None,
    duplicate_source: Tag | None = None,
) -> Element:
    """Render the tag create/edit form.

    ``tag`` — when present, edit that tag. ``duplicate_source`` — when present
    (and ``tag`` is None), prefill a new tag from this row.
    """
    if tag is not None and duplicate_source is not None:
        message = "tag_form: pass either `tag` or `duplicate_source`, not both."
        raise ValueError(message)

    prefill: Tag | None = tag if tag is not None else duplicate_source
    selected_implications: list[Tag] = list(prefill.implications) if prefill else []
    current_aliases: list[str] = [a.alias for a in prefill.aliases] if prefill else []
    return html_base(
        title="Create Tag" if not tag else "Edit Tag",
        body_content=centered_div(
            content=[
                page_heading(
                    icon="tag" if not tag else "pencil",
                    text="Create a Tag" if not tag else "Edit a Tag",
                ),
                duplicate_source is not None
                and _duplicate_notice(
                    source_display_name=duplicate_source.display_name,
                ),
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
                        value=prefill.display_name if prefill else None,
                    ),
                    label(for_="md-editor-description")["Description"],
                    markdown_editor(
                        field_id="description",
                        name="description",
                        value=prefill.description if prefill else None,
                    ),
                    label(for_="category")["Category"],
                    select(name="category", id="category", class_="single-select")[
                        [
                            option(
                                value=cat.value,
                                selected=cat
                                == (
                                    prefill.category if prefill else TagCategory.general
                                ),
                                data_icon=CATEGORY_ICONS[cat],
                                data_color=CATEGORY_COLORS[cat],
                                data_category=cat.value,
                            )[titlecase(cat.value)]
                            for cat in TagCategory
                        ]
                    ],
                    label(for_="implication_ids")["Child of"],
                    select(
                        name="implication_ids",
                        id="implication_ids",
                        multiple=True,
                        class_="multi-select",
                        data_options_url=options_url,
                    )[
                        [
                            option(
                                value=t.id,
                                selected=True,
                                data_icon=CATEGORY_ICONS.get(t.category, "tag"),
                                data_color=CATEGORY_COLORS.get(t.category, ""),
                                data_category=t.category.value,
                            )["(P) " + t.name if t.is_pending else t.name]
                            for t in selected_implications
                        ]
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
        script_content=Markup(_INIT_SCRIPT),
        request=request,
    )
