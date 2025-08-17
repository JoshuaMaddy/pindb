from fastapi.datastructures import URL
from htpy import div, form, input, label

from pindb.templates.base import html_base


def material_form(post_url: URL | str):
    return html_base(
        form(hx_post=str(post_url))[
            div[
                label(for_="name")["Name"],
                input(type="text", name="name", id="name", required=True),
            ],
            input(type="submit", value="Submit"),
        ]
    )
