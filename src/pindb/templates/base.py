"""
htpy page and fragment builders: `templates/base.py`.
"""

import json
from collections.abc import Sequence

from fastapi import Request
from htpy import body, div, head, html, link, meta, script
from htpy import main as main_el
from htpy import title as title_el
from markupsafe import Markup

from pindb.asset_cache_buster import STATIC_CACHE_BUSTER
from pindb.templates.components.nav.bread_crumb import BreadCrumbLink
from pindb.templates.components.shell.footer import footer
from pindb.templates.components.shell.navbar import navbar
from pindb.templates.components.tags.tag_branding import CATEGORY_COLORS, CATEGORY_ICONS
from pindb.templates.js_urls import templates_js_url
from pindb.templates.types import Content

_TAG_CATEGORY_JSON: str = json.dumps(
    {
        cat.value: {"icon": CATEGORY_ICONS[cat], "color": CATEGORY_COLORS[cat]}
        for cat in CATEGORY_ICONS
    }
).replace("</", "<\\/")


def html_base(
    body_content: Content,
    template_js_extra: Sequence[str] = (),
    head_content: Content = None,
    bread_crumb_links: list[BreadCrumbLink | str] | None = None,
    title: str = "Document",
    request: Request | None = None,
):
    theme: str = getattr(request.state, "theme", "mocha") if request else "mocha"
    extra_scripts = [
        script(src=templates_js_url(name), defer=True) for name in template_js_extra
    ]
    return html(lang="en", class_=f"{theme} bg-darker")[
        head[
            meta(charset="UTF-8"),
            meta(name="viewport", content="width=device-width, initial-scale=1.0"),
            link(rel="icon", href="/static/favicon.png"),
            script(
                src=f"/static/vendor/htmx.min.js?v={STATIC_CACHE_BUSTER}",
                defer=True,
            ),
            script(
                src=f"/static/vendor/notyf.min.js?v={STATIC_CACHE_BUSTER}",
                defer=True,
            ),
            script(
                src=f"/static/vendor/tom-select.complete.min.js?v={STATIC_CACHE_BUSTER}",
                defer=True,
            ),
            link(
                rel="stylesheet",
                href=f"/static/vendor/tom-select.default.min.css?v={STATIC_CACHE_BUSTER}",
            ),
            link(
                rel="stylesheet",
                href=f"/static/vendor/notyf.min.css?v={STATIC_CACHE_BUSTER}",
            ),
            link(
                rel="stylesheet",
                href=f"/static/main.css?v={STATIC_CACHE_BUSTER}",
            ),
            title_el[title + " | PinDB"],
            head_content,
            script(**{"type": "application/json"}, id="pindb-tag-category-data")[
                Markup(_TAG_CATEGORY_JSON)
            ],
            script(
                src=templates_js_url("tables/data_table_alpine_register.js"),
                defer=True,
            ),
            script(
                src=f"/static/vendor/alpine.min.js?v={STATIC_CACHE_BUSTER}",
                defer=True,
            ),
            script(
                src=f"/static/vendor/overtype.min.js?v={STATIC_CACHE_BUSTER}",
                defer=True,
            ),
            script(
                src=f"/static/vendor/marked.min.js?v={STATIC_CACHE_BUSTER}",
                defer=True,
            ),
        ],
        body(class_="min-h-screen flex flex-col")[
            navbar(request=request),
            main_el(class_="min-h-screen relative z-5")[body_content,],
            footer(),
            div(
                id="pindb-toast-host",
                class_="sr-only",
                aria_live="polite",
            ),
        ],
        script(
            src=f"/static/vendor/lucide.min.js?v={STATIC_CACHE_BUSTER}",
            defer=True,
        ),
        script(src=templates_js_url("shell/pindb_shell.js"), defer=True),
        script(src=templates_js_url("tags/tag_category_bootstrap.js"), defer=True),
        script(src=templates_js_url("tags/tag_select.js"), defer=True),
        script(src=templates_js_url("forms/form_persist.js"), defer=True),
        script(src=templates_js_url("forms/markdown_editor.js"), defer=True),
        script(src=templates_js_url("forms/form_validate.js"), defer=True),
        script(src=templates_js_url("forms/htmx_submit_guard.js"), defer=True),
        *extra_scripts,
    ]
