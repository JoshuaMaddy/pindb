from fastapi.datastructures import URL
from htpy import Element, a, i


def card_link(
    href: str | URL,
    text: str,
    icon: str | None = None,
) -> Element:
    return a(
        href=str(href),
        class_="p-2 no-underline text-pin-base-text bg-pin-main hover:border-accent hover:bg-pin-main-hover rounded-xl border border-pin-base-350",
    )[
        icon
        and i(
            data_lucide=icon,
            class_="inline-block pb-1 pr-2",
        ),
        text,
    ]
