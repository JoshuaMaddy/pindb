from pathlib import Path

from fastapi.datastructures import URL
from htpy import br, button, div, form, input, label, textarea

from pindb.templates.base import html_base

with open(
    Path(__file__).parent.parent / "js/pin_creation.js", "r", encoding="utf-8"
) as js_file:
    SCRIPT_CONTENT = js_file.read()


def shop_form(post_url: URL | str):
    return html_base(
        form(
            class_="max-w-[40ch]",
            hx_post=str(post_url),
        )[
            div(class_="flex justify-between gap-2")[
                label(for_="name")["Name"],
                input(
                    type="text", name="name", id="name", required=True, class_="grow"
                ),
            ],
            div[
                label(for_="description")["Description"],
                br,
                textarea(id="description", name="description", class_="w-full"),
            ],
            div[
                label(for_="links")["Links"],
                div(id="links", class_="grid grid-cols-[1fr_8em] gap-2")[
                    input(
                        name="links",
                        id="link_0",
                        type="text",
                        class_="col-span-2",
                    ),
                ],
                br,
                button(id="add-link-button")["Add Link"],
            ],
            input(type="submit", value="Submit"),
        ],
        script_content=SCRIPT_CONTENT,
    )
