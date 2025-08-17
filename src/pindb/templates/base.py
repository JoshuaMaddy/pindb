from htpy import BaseElement, Fragment, body, head, html, link, meta, script, title


def html_base(body_content: BaseElement | Fragment):
    return html(lang="en")[
        head[
            meta(charset="UTF-8"),
            meta(name="viewport", content="width=device-width, initial-scale=1.0"),
            script(src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.6/dist/htmx.min.js"),
            script(
                src="https://cdn.jsdelivr.net/npm/tom-select@2.4.3/dist/js/tom-select.complete.min.js"
            ),
            link(
                rel="stylesheet",
                href="https://cdn.jsdelivr.net/npm/tom-select@2.4.3/dist/css/tom-select.default.min.css",
            ),
            title["Document"],
        ],
        body[body_content],
    ]
