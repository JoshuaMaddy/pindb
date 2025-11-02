from fastapi.datastructures import URL
from htpy import form, h1, hr, input, label

from pindb.database.tag import Tag
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div


def tag_form(post_url: URL | str, tag: Tag | None = None):
    return html_base(
        body_content=centered_div(
            [
                h1["Create a Tag" if not tag else "Edit a Tag"],
                hr,
                form(
                    hx_post=str(post_url),
                    class_="flex flex-col gap-2 [&_label]:font-semibold",
                )[
                    label(for_="name")["Name"],
                    input(
                        type="text",
                        name="name",
                        id="name",
                        required=True,
                        value=tag.name if tag else None,
                    ),
                    input(
                        type="submit",
                        value="Submit",
                        class_="mt-2",
                    ),
                ],
            ]
        )
    )
