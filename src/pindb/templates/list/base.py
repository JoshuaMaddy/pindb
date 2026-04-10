from fastapi import Request
from htpy import Element, div, h1, hr

from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div


def base_list(
    title: str,
    items: list[Element],
    bread_crumb: Element | None = None,
    request: Request | None = None,
) -> Element:
    return html_base(
        title=title,
        request=request,
        body_content=centered_div(
            content=[
                bread_crumb,
                div[
                    h1[title],
                    hr,
                ],
                *items,
            ],
            flex=True,
            col=True,
        ),
    )
