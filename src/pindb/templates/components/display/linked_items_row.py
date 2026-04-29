"""
htpy page and fragment builders: `templates/components/display/linked_items_row.py`.
"""

from typing import Iterable, Literal

from htpy import Element, VoidElement, div, h2, h3, i


def linked_items_row(
    icon: str,
    label: str,
    items: Iterable[Element | VoidElement],
    *,
    heading_level: Literal[2, 3] = 2,
) -> Element:
    """Flex-wrap row with an icon + label heading followed by inline items (links, text).

    *heading_level* must match the surrounding outline: use ``2`` when the page
    title is ``h1`` (e.g. tag/shop/artist pages); use ``3`` when this row sits
    under an ``h2`` section (e.g. pin details under "Details").
    """
    heading = h2 if heading_level == 2 else h3
    label_class = "text-base font-semibold sm:text-lg m-0"
    return div(class_="flex flex-wrap gap-2 items-baseline")[
        heading(class_=label_class)[
            i(data_lucide=icon, class_="inline-block pr-2", aria_hidden="true"),
            label,
        ],
        *items,
    ]
