from fastapi.datastructures import URL
from htpy import div, form, h1, hr, input, label

from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div


def search_pin_form(post_url: URL | str):
    return html_base(
        body_content=centered_div(
            [
                h1["Search"],
                hr,
                form(
                    hx_post=str(post_url),
                    hx_target="#results",
                    class_="flex flex-col gap-2 [&_label]:font-semibold",
                )[
                    label(for_="search")["Search"],
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
                ],
                div("#results"),
            ]
        )
    )
