from htpy import Element, a


def pill_link(href: str, text: str) -> Element:
    return a(
        href=href,
        class_="px-2 py-1 rounded-lg border border-pin-base-400 bg-pin-base-500 text-sm no-underline hover:border-accent text-pin-base-text hover:text-accent",
    )[text]
