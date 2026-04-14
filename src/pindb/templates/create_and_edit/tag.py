from typing import Sequence

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
function _tagRenderOption(data, escape) {
    var icon = data.icon || 'tag';
    var color = data.color || '';
    return '<div class="flex items-center gap-2">' +
        '<span class="inline-flex items-center p-0.5 rounded border ' + color + '">' +
        '<i data-lucide="' + icon + '" class="w-3.5 h-3.5"></i>' +
        '</span>' +
        '<span>' + escape(data.text) + '</span>' +
        '</div>';
}

function _tagRenderItem(data, escape) {
    var icon = data.icon || 'tag';
    var color = data.color || '';
    return '<div class="inline-flex items-center gap-1">' +
        '<span class="inline-flex items-center p-0.5 rounded border ' + color + '">' +
        '<i data-lucide="' + icon + '" class="w-3 h-3"></i>' +
        '</span>' +
        '<span>' + escape(data.text) + '</span>' +
        '</div>';
}

function _tagSelectCallbacks() {
    return {
        onDropdownOpen: function() { lucide.createIcons(); },
        onItemAdd: function() { requestAnimationFrame(function() { lucide.createIcons(); }); },
        onInitialize: function() { lucide.createIcons(); }
    };
}

document.querySelectorAll("select.multi-select").forEach(function(el) {
    new TomSelect(el, Object.assign({
        maxItems: null,
        plugins: ["caret_position", "remove_button"],
        render: { option: _tagRenderOption, item: _tagRenderItem }
    }, _tagSelectCallbacks()));
});

document.querySelectorAll("select.single-select").forEach(function(el) {
    new TomSelect(el, Object.assign({
        render: { option: _tagRenderOption, item: _tagRenderItem }
    }, _tagSelectCallbacks()));
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
    all_tags: Sequence[Tag],
    tag: Tag | None = None,
) -> Element:
    current_implications: set[int] = {t.id for t in tag.implications} if tag else set()
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
                    class_="flex flex-col gap-2 [&_label]:font-semibold",
                )[
                    label(for_="name")["Name", span(class_="text-red-200 ml-0.5")["*"]],
                    input(
                        type="text",
                        name="name",
                        id="name",
                        required=True,
                        value=tag.name if tag else None,
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
                    )[
                        [
                            option(
                                value=t.id,
                                selected=t.id in current_implications,
                                data_icon=CATEGORY_ICONS.get(t.category, "tag"),
                                data_color=CATEGORY_COLORS.get(t.category, ""),
                            )["(P) " + t.name if t.is_pending else t.name]
                            for t in all_tags
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
