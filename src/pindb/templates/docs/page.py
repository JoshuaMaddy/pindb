"""
htpy page and fragment builders: `templates/docs/page.py`.
"""

from dataclasses import dataclass

from fastapi import Request
from htpy import Element, a, aside, div, h2, li, nav, ul
from markupsafe import Markup

from pindb.templates.base import html_base


@dataclass
class DocEntry:
    slug: str
    title: str
    order: int


@dataclass
class DocSection:
    key: str
    label: str
    entries: list[DocEntry]


def docs_page(
    request: Request,
    section: DocSection,
    current_slug: str,
    rendered_html: str,
    page_title: str,
) -> Element:
    return html_base(
        title=page_title,
        request=request,
        body_content=div(
            class_="flex min-h-screen w-full max-w-6xl mx-auto px-4 py-6 gap-6"
        )[
            _sidebar(section=section, current_slug=current_slug),
            div(class_="flex-1 min-w-0")[
                div(class_="prose max-w-none doc-content")[Markup(rendered_html)]
            ],
        ],
    )


def _sidebar(section: DocSection, current_slug: str) -> Element:
    return aside(class_="w-56 shrink-0 sticky top-4 self-start hidden md:block")[
        nav[
            h2(
                class_="text-xs font-semibold uppercase tracking-wider text-lightest-hover mb-3"
            )[section.label],
            ul(class_="flex flex-col gap-1")[
                [
                    li[
                        a(
                            href=f"/docs/{section.key}/{entry.slug}",
                            class_=(
                                "block px-2 py-1 rounded text-sm font-medium "
                                "bg-main text-base-text"
                                if entry.slug == current_slug
                                else "block px-2 py-1 rounded text-sm text-base-text hover:bg-main-hover hover:text-base-text"
                            ),
                        )[entry.title]
                    ]
                    for entry in section.entries
                ]
            ],
        ]
    ]
