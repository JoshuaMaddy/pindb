from fastapi.datastructures import URL
from htpy import Element, div, form, h1, hr, input

from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div


def search_pin_input(post_url: URL | str, hx_target: str = "#results") -> Element:
    return form(
        hx_post=str(post_url),
        hx_target=hx_target,
        class_="flex flex-col gap-2 [&_label]:font-semibold",
    )[
        input(
            type="text",
            name="search",
            id="search",
            required=True,
        ),
        input(
            type="submit",
            value="Submit",
            class_="mt-2",
        ),
    ]


def search_pin_page(post_url: URL | str):
    return html_base(
        title="Search",
        body_content=centered_div(
            content=[
                h1["Search"],
                hr,
                search_pin_input(post_url=post_url),
                div("#results", class_="mt-4"),
            ],
            wide=True,
        ),
    )
