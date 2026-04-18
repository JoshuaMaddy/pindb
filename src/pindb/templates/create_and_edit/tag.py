from fastapi import Request
from fastapi.datastructures import URL
from htpy import Element, form, hr, input, label, option, select, span
from markupsafe import Markup

from pindb.database.tag import Tag, TagCategory
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div
from pindb.templates.components.markdown_editor import markdown_editor
from pindb.templates.components.page_heading import page_heading
from pindb.templates.components.tag_branding import CATEGORY_COLORS, CATEGORY_ICONS

_INIT_SCRIPT = """
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
"""


def tag_form(
    post_url: URL | str,
    request: Request,
    options_url: str,
    tag: Tag | None = None,
) -> Element:
    selected_implications: list[Tag] = list(tag.implications) if tag else []
    current_aliases: list[str] = [a.alias for a in tag.aliases] if tag else []
    return html_base(
        title="Create Tag" if not tag else "Edit Tag",
        body_content=centered_div(
            content=[
                page_heading(
                    icon="tag" if not tag else "pencil",
                    text="Create a Tag" if not tag else "Edit a Tag",
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
                        value=tag.display_name if tag else None,
                    ),
                    label(for_="md-editor-description")["Description"],
                    markdown_editor(
                        field_id="description",
                        name="description",
                        value=tag.description if tag else None,
                    ),
                    label(for_="category")["Category"],
                    select(name="category", id="category", class_="single-select")[
                        [
                            option(
                                value=cat.value,
                                selected=cat
                                == (tag.category if tag else TagCategory.general),
                                data_icon=CATEGORY_ICONS[cat],
                                data_color=CATEGORY_COLORS[cat],
                                data_category=cat.value,
                            )[cat.value.title()]
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
