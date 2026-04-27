"""
htpy page and fragment builders: `templates/components/card.py`.
"""

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
        class_="p-2 no-underline text-base-text bg-main rounded-xl border border-lightest flex gap-2 "
        + (additional_classes + " " if additional_classes else "")
        + "cursor-pointer hover:scale-[102%] hover:border-accent hover:bg-main-hover transition-all duration-100 ease-linear"
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
