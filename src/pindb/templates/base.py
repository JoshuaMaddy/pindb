from htpy import BaseElement, Fragment, body, head, html, link, meta, script
from htpy import title as title_el
from markupsafe import Markup

from pindb.templates.components.bread_crumb import BreadCrumbLink, bread_crumb
from pindb.templates.components.navbar import navbar


def html_base(
    body_content: BaseElement | Fragment | list[BaseElement | Fragment],
    script_content: BaseElement | str | None = None,
    bread_crumb_links: list[BreadCrumbLink | str] | None = None,
    title: str = "Document",
):
    return html(lang="en", class_="mocha bg-pin-base-550")[
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
                href="/static/main.css",
            ),
            title_el[title + " | PinDB"],
        ],
        body()[
            navbar(),
            bread_crumb(entries=bread_crumb_links),
            body_content,
        ],
        script(src="https://unpkg.com/lucide@latest"),
        script["lucide.createIcons();"],
        script[
            Markup(
                """
var element = document.getElementById('back-link');
if (element != null){
    element.setAttribute('href', document.referrer);
    element.onclick = function() {
    history.back();
    return false;
    }
}
"""
            )
        ],
        script_content and script[Markup(script_content)],
    ]
