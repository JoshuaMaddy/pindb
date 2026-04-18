from typing import Iterable

from htpy import Element, VoidElement, div, i, p


def linked_items_row(
    icon: str,
    label: str,
    items: Iterable[Element | VoidElement],
) -> Element:
    """Flex-wrap row with an icon + bold label heading followed by inline items (links, text)."""
    return div(class_="flex flex-wrap gap-2 items-baseline")[
        p(class_="text-base font-semibold sm:text-lg")[
            i(data_lucide=icon, class_="inline-block pr-2"),
            label,
        ],
        *items,
    ]
