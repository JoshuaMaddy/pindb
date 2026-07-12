"""
htpy component: `templates/components/display/entity_links.py`.

Renders an artist/shop's Link list: known-brand domains (Instagram, X,
Bluesky, Etsy, ...) collapse into a horizontal row of icon-only links with
the raw URL as a hover tooltip; everything else keeps the plain URL list.
"""

from typing import Iterable
from urllib.parse import urlsplit

from htpy import Element, Fragment, a, br, div, fragment, h2, path, svg

from pindb.database.link import Link
from pindb.templates.components.display.brand_icons import (
    BRAND_ICONS_BY_DOMAIN,
    BrandIcon,
)


def _domain_of(url: str) -> str:
    host = urlsplit(url).netloc.lower()
    if host.startswith("www."):
        host = host[len("www.") :]
    return host


def _brand_icon_for(url: str) -> BrandIcon | None:
    domain = _domain_of(url)
    for known_domain, icon in BRAND_ICONS_BY_DOMAIN.items():
        if domain == known_domain or domain.endswith(f".{known_domain}"):
            return icon
    return None


def _brand_icon_link(link: Link, icon: BrandIcon) -> Element:
    return a(
        href=link.path,
        target="_blank",
        rel="noopener noreferrer",
        title=link.path,
        aria_label=f"{icon.title}: {link.path}",
        class_=(
            "inline-flex items-center justify-center w-9 h-9 rounded-full "
            "border border-accent bg-transparent text-accent "
            "hover:bg-accent hover:text-darker transition-colors duration-500"
        ),
    )[
        svg(
            viewBox="0 0 24 24",
            class_="w-5 h-5",
            fill="currentColor",
            aria_hidden="true",
        )[path(d=icon.path)]
    ]


def entity_links(links: Iterable[Link]) -> Fragment:
    """Horizontal known-domain icon row (if any) plus a plain list of the rest."""
    icon_links: list[tuple[Link, BrandIcon]] = []
    other_links: list[Link] = []
    for link in links:
        icon = _brand_icon_for(link.path)
        if icon is not None:
            icon_links.append((link, icon))
        else:
            other_links.append(link)

    return fragment[
        bool(icon_links)
        and div(class_="flex flex-wrap gap-2 items-center")[
            *[_brand_icon_link(link, icon) for link, icon in icon_links]
        ],
        bool(other_links)
        and div[
            h2["Links"],
            *[fragment[a(href=link.path)[link.path], br] for link in other_links],
        ],
    ]
