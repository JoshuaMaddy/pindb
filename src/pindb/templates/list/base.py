from htpy import Element, div, h1

from pindb.templates.base import html_base


def base_list(title: str, items: list[Element]) -> Element:
    return html_base(
        body_content=div(class_="max-w-[80ch] mx-auto p-10 flex flex-col gap-2")[
            h1[title],
            *items,
        ]
    )
