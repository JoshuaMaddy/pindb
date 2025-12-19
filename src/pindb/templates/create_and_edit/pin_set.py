from fastapi.datastructures import URL
from htpy import Element, form, h1, hr, input, label

from pindb.database.pin_set import PinSet
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div


def pin_set_form(
    post_url: URL | str,
    pin_set: PinSet | None = None,
) -> Element:
    return html_base(
        title="Create Pin Set" if not pin_set else "Edit Pin Set",
        body_content=centered_div(
            content=[
                h1["Create a Pin Set" if not pin_set else "Edit a Pin Set"],
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
                        value=pin_set.name if pin_set else None,
                    ),
                    input(
                        type="submit",
                        value="Submit",
                        class_="mt-2",
                    ),
                ],
            ]
        ),
    )
