"""
htpy page and fragment builders: `templates/docs/index.py`.
"""

from fastapi import Request
from htpy import Element, a, div, h1, li, p, ul

from pindb.templates.base import html_base
from pindb.templates.docs.page import DocSection


def docs_index(request: Request, sections: list[DocSection]) -> Element:
    return html_base(
        title="Documentation",
        request=request,
        body_content=div(class_="w-full max-w-4xl mx-auto px-4 py-8")[
            h1(class_="mb-2")["Documentation"],
            p(class_="text-pin-base-text mb-8")[
                "Guides and reference material for editors and contributors."
            ],
            div(class_="grid gap-4 sm:grid-cols-2")[
                [_section_card(s) for s in sections]
            ],
        ],
    )


def _section_card(section: DocSection) -> Element:
    first = section.entries[0] if section.entries else None
    href = f"/docs/{section.key}/{first.slug}" if first else f"/docs/{section.key}"
    return div(class_="bg-pin-base-500 border border-lightest rounded-lg p-5")[
        a(class_="text-accent hover:underline text-lg font-semibold", href=href)[
            section.label
        ],
        ul(class_="mt-3 flex flex-col gap-1")[
            [
                li[
                    a(
                        class_="text-pin-base-text hover:text-accent text-sm",
                        href=f"/docs/{section.key}/{entry.slug}",
                    )[entry.title]
                ]
                for entry in section.entries
            ]
        ],
    ]
