from pathlib import Path

from fastapi.datastructures import URL
from htpy import Element, button, div, form, fragment, h1, hr, input, label, textarea

from pindb.database.link import Link
from pindb.database.shop import Shop
from pindb.templates.base import html_base
from pindb.templates.components.centered import centered_div

with open(
    file=Path(__file__).parent.parent / "js/pin_creation.js",
    mode="r",
    encoding="utf-8",
) as js_file:
    SCRIPT_CONTENT: str = js_file.read()


def shop_form(
    post_url: URL | str,
    shop: Shop | None = None,
) -> Element:
    shop_links: None | list[Link] = None
    if shop:
        shop_links = list(shop.links)

    return html_base(
        title="Create Shop" if not shop else "Edit Shop",
        body_content=centered_div(
            content=[
                h1["Create a Shop" if not shop else "Edit a Shop"],
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
                        class_="grow",
                        value=shop.name if shop else None,
                    ),
                    label(for_="description")["Description"],
                    textarea(
                        id="description",
                        name="description",
                        class_="w-full",
                        value=shop.description if shop else None,
                    ),
                    div[
                        label(for_="links")["Links"],
                        div(
                            id="links", class_="grid grid-cols-[1fr_min-content] gap-2"
                        )[
                            input(
                                name="links",
                                id="link_0",
                                type="text",
                                class_="col-span-2",
                                value=shop_links.pop(0).path if shop_links else None,
                            ),
                            (shop_links is not None and len(shop_links) != 0)
                            and [
                                fragment[
                                    input(
                                        name="links",
                                        id=f"link_{i}",
                                        type="text",
                                        value=link.path,
                                    ),
                                    button(class_="remove-link-button")["Remove"],
                                ]
                                for i, link in enumerate(shop_links)
                            ],
                        ],
                        button(
                            id="add-link-button",
                            class_="w-full mt-2",
                            type="button",
                        )["Add Link"],
                    ],
                    input(
                        type="submit",
                        value="Submit",
                        class_="mt-2",
                    ),
                ],
            ]
        ),
        script_content=SCRIPT_CONTENT,
    )
