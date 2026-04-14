from htpy import Element, div, h1, h2, i

from pindb.templates.types import Content


def page_heading(
    icon: str,
    text: str | Element,
    extras: Content | None = None,
    level: int = 1,
    full_width: bool = False,
) -> Element:
    """Icon + heading in a flex-baseline row. Extras are appended after the heading text."""
    heading_el: Element = h1[text] if level == 1 else h2[text]
    classes = "flex gap-2 items-baseline"
    if full_width:
        classes += " w-full"
    return div(class_=classes)[
        i(data_lucide=icon),
        heading_el,
        extras,
    ]
