from fastapi.datastructures import URL
from htpy import Element, div, i

from pindb.templates.components.centered import Content


def card(
    href: str | URL | None = None,
    icon: str | None = None,
    content: Content = None,
    additional_classes: str = "",
) -> Element:
    return div(
        onclick=f"window.location.href='{str(href)}'" if href else None,
        class_="p-2 no-underline text-pin-base-text bg-pin-main rounded-xl border border-pin-base-350 flex gap-2 "
        + additional_classes
        + "cursor-pointer hover:scale-[102%] hover:border-accent hover:bg-pin-main-hover"
        if href
        else "",
    )[
        icon
        and i(
            data_lucide=icon,
            class_="inline-block",
        ),
        content,
    ]
