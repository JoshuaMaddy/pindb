from fastapi import Request
from htpy import Element, div, h1, h2

from pindb.templates.base import html_base
from pindb.templates.list.index import list_index


def homepage(request: Request) -> Element:
    return html_base(
        title="Home",
        body_content=div(class_="w-full flex flex-col gap-2 grow-0 mt-5")[
            h1(class_="text-center")["PinDB"],
            h2(class_="text-center")["A database for all things pins."],
            div(class_="flex flex-col gap-2 max-w-[60ch] mx-auto grow w-full")[
                list_index(request=request, header=False),
            ],
        ],
    )
