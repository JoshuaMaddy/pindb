"""
htpy page and fragment builders: `templates/components/page_heading.py`.
"""

from htpy import Element, div, h1, h2, i

from pindb.templates.types import Content


def page_heading(
    icon: str,
    text: str | Element,
    extras: Content | None = None,
    level: int = 1,
    full_width: bool = False,
) -> Element:
    """Icon + heading; optional extras sit after the title on large screens, below on small."""
    heading_el: Element = (
        h1(class_="min-w-0 wrap-break-word")[text]
        if level == 1
        else h2(class_="min-w-0 wrap-break-word")[text]
    )
    title_row: Element = div(class_="flex gap-2 items-baseline min-w-0")[
        i(data_lucide=icon, class_="shrink-0", aria_hidden="true"),
        heading_el,
    ]
    outer: str = "flex flex-col gap-2 min-w-0 sm:flex-row sm:items-baseline sm:gap-2"
    if full_width:
        outer += " w-full"

    if extras is None:
        return div(class_=outer)[title_row]

    return div(class_=outer)[
        title_row,
        div(class_="flex flex-wrap items-center gap-2 shrink-0")[extras],
    ]
