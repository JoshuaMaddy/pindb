"""
htpy page and fragment builders: `templates/base.py`.
"""

import json
import time
from pathlib import Path

from fastapi import Request
from htpy import BaseElement, body, div, head, html, link, meta, script
from htpy import main as main_el
from htpy import title as title_el
from markupsafe import Markup

from pindb.templates.components.bread_crumb import BreadCrumbLink
from pindb.templates.components.footer import footer
from pindb.templates.components.navbar import navbar
from pindb.templates.components.tag_branding import CATEGORY_COLORS, CATEGORY_ICONS
from pindb.templates.types import Content

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

with open(
    file=Path(__file__).parent / "js/form_validate.js",
    mode="r",
    encoding="utf-8",
) as _fp:
    _FORM_VALIDATE_SCRIPT: str = _fp.read()


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
            script(
                src=f"/static/vendor/htmx.min.js?v={_STARTUP_TIME}",
                defer=True,
            ),
            script(
                src=f"/static/vendor/notyf.min.js?v={_STARTUP_TIME}",
                defer=True,
            ),
            script(
                src=f"/static/vendor/tom-select.complete.min.js?v={_STARTUP_TIME}",
                defer=True,
            ),
            link(
                rel="stylesheet",
                href=f"/static/vendor/tom-select.default.min.css?v={_STARTUP_TIME}",
            ),
            link(
                rel="stylesheet",
                href=f"/static/vendor/notyf.min.css?v={_STARTUP_TIME}",
            ),
            link(
                rel="stylesheet",
                href=f"/static/main.css?v={_STARTUP_TIME}",
            ),
            title_el[title + " | PinDB"],
            script(
                src=f"/static/vendor/alpine.min.js?v={_STARTUP_TIME}",
                defer=True,
            ),
            script(
                src=f"/static/vendor/overtype.min.js?v={_STARTUP_TIME}",
                defer=True,
            ),
            script(
                src=f"/static/vendor/marked.min.js?v={_STARTUP_TIME}",
                defer=True,
            ),
        ],
        body(class_="min-h-screen flex flex-col")[
            navbar(request=request),
            main_el(class_="min-h-screen")[body_content,],
            footer(),
            div(
                id="pindb-toast-host",
                class_="sr-only",
                aria_live="polite",
            ),
        ],
        script(
            src=f"/static/vendor/lucide.min.js?v={_STARTUP_TIME}",
            defer=True,
        ),
        script[
            Markup(
                object="""
(function () {
  function pindbAfterVendorScripts() {
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
    window.pindbNotyf = new Notyf({
        dismissible: true,
        duration: 4500,
        position: { x: 'right', y: 'bottom' },
        ripple: true,
    });
    document.addEventListener('pindbToast', function (evt) {
        var d = evt.detail;
        if (!d || typeof d !== 'object') {
            return;
        }
        var msg = d.message;
        if (!msg) {
            return;
        }
        var typ = d.type || 'success';
        if (typ === 'success') {
            window.pindbNotyf.success(msg);
        } else {
            window.pindbNotyf.error(msg);
        }
    });
    document.body.addEventListener('htmx:afterSwap', function(evt) {
        lucide.createIcons();
        var target = evt.detail.target;
        if (!target || target.id !== 'pindb-toast-host') {
            return;
        }
        var sig = target.querySelector('#pindb-toast-signal');
        if (!sig) {
            return;
        }
        var msg = sig.dataset.pindbMessage;
        if (!msg) {
            target.innerHTML = '';
            return;
        }
        var typ = sig.dataset.pindbType || 'error';
        if (typ === 'success') {
            window.pindbNotyf.success(msg);
        } else {
            window.pindbNotyf.error(msg);
        }
        target.innerHTML = '';
    });
    if (window.lucide) {
        lucide.createIcons();
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', pindbAfterVendorScripts);
  } else {
    pindbAfterVendorScripts();
  }
})();
"""
            )
        ],
        script[Markup(object=_TAG_CATEGORY_DATA_JS)],
        script[Markup(object=_TAG_SELECT_SCRIPT)],
        script[Markup(object=_FORM_PERSIST_SCRIPT)],
        script[Markup(object=_MARKDOWN_EDITOR_SCRIPT)],
        script[Markup(object=_FORM_VALIDATE_SCRIPT)],
        script_content and script[Markup(object=script_content)],
    ]
