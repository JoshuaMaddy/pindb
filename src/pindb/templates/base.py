import json
import time
from pathlib import Path

from fastapi import Request
from htpy import BaseElement, body, head, html, link, meta, script
from htpy import title as title_el
from markupsafe import Markup

from pindb.templates.components.tag_branding import CATEGORY_COLORS, CATEGORY_ICONS

_TAG_CATEGORY_DATA_JS: str = (
    "window.TagCategoryData = "
    + json.dumps(
        {
            cat.value: {"icon": CATEGORY_ICONS[cat], "color": CATEGORY_COLORS[cat]}
            for cat in CATEGORY_ICONS
        }
    )
    + ";"
)

with open(
    file=Path(__file__).parent / "js/tag_select.js",
    mode="r",
    encoding="utf-8",
) as _fp:
    _TAG_SELECT_SCRIPT: str = _fp.read()

with open(
    file=Path(__file__).parent / "js/form_persist.js",
    mode="r",
    encoding="utf-8",
) as _fp:
    _FORM_PERSIST_SCRIPT: str = _fp.read()

with open(
    file=Path(__file__).parent / "js/markdown_editor.js",
    mode="r",
    encoding="utf-8",
) as _fp:
    _MARKDOWN_EDITOR_SCRIPT: str = _fp.read()

from pindb.templates.components.bread_crumb import BreadCrumbLink, bread_crumb
from pindb.templates.components.navbar import navbar
from pindb.templates.types import Content

_STARTUP_TIME = int(time.time())


def html_base(
    body_content: Content,
    script_content: BaseElement | str | None = None,
    bread_crumb_links: list[BreadCrumbLink | str] | None = None,
    title: str = "Document",
    request: Request | None = None,
):
    theme: str = getattr(request.state, "theme", "mocha") if request else "mocha"
    return html(lang="en", class_=f"{theme} bg-pin-base-550")[
        head[
            meta(charset="UTF-8"),
            meta(name="viewport", content="width=device-width, initial-scale=1.0"),
            link(rel="icon", href="/static/favicon.png"),
            # HTMX
            script(src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.6/dist/htmx.min.js"),
            script(
                src="https://cdn.jsdelivr.net/npm/tom-select@2.4.3/dist/js/tom-select.complete.min.js"
            ),
            # Tom Select
            link(
                rel="stylesheet",
                href="https://cdn.jsdelivr.net/npm/tom-select@2.4.3/dist/css/tom-select.default.min.css",
            ),
            # Custom styles
            link(
                rel="stylesheet",
                href=f"/static/main.css?v={_STARTUP_TIME}",
            ),
            title_el[title + " | PinDB"],
            # Alpine
            script(
                src="https://cdn.jsdelivr.net/npm/alpinejs@3.15.3/dist/cdn.min.js",
                defer=True,
            ),
            # Overtype markdown editor
            script(
                src="https://cdn.jsdelivr.net/npm/overtype@latest/dist/overtype.min.js"
            ),
            # marked (client-side markdown preview)
            script(src="https://cdn.jsdelivr.net/npm/marked@9/marked.min.js"),
        ],
        body()[
            navbar(request=request),
            bread_crumb(entries=bread_crumb_links),
            body_content,
        ],
        script(src="https://unpkg.com/lucide@latest"),
        script["lucide.createIcons();"],
        script[
            Markup(
                object="""
var element = document.getElementById('back-link');
if (element != null) {
    var storageKey = 'pin_back:' + window.location.pathname;
    var params = new URLSearchParams(window.location.search);
    var backUrl = params.get('back');
    if (backUrl) {
        sessionStorage.setItem(storageKey, backUrl);
        element.setAttribute('href', backUrl);
    } else {
        var stored = sessionStorage.getItem(storageKey);
        if (stored) {
            element.setAttribute('href', stored);
        } else {
            element.setAttribute('href', document.referrer || '#');
            element.onclick = function() { history.back(); return false; };
        }
    }
}
document.body.addEventListener('htmx:afterSwap', function() {
    lucide.createIcons();
});
"""
            )
        ],
        script[Markup(object=_TAG_CATEGORY_DATA_JS)],
        script[Markup(object=_TAG_SELECT_SCRIPT)],
        script[Markup(object=_FORM_PERSIST_SCRIPT)],
        script[Markup(object=_MARKDOWN_EDITOR_SCRIPT)],
        script_content and script[Markup(object=script_content)],
    ]
