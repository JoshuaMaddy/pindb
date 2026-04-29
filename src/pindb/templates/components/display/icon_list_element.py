"""
htpy page and fragment builders: `templates/components/display/icon_list_element.py`.
"""

from typing import Literal

from htpy import Element, div, h2, h3, i


def icon_list_item(
    icon: str,
    name: str,
    value: str,
    *,
    heading_level: Literal[2, 3] = 3,
) -> Element:
    """Icon + bold heading followed by an inline value.

    *heading_level* must match the surrounding outline (defaults to ``3`` for
    use under an ``h2`` section like the pin "Details" aside).
    """
    heading = h2 if heading_level == 2 else h3
    return div(class_="flex flex-wrap gap-2 items-baseline")[
        heading(class_="text-base font-semibold sm:text-lg m-0")[
            i(
                data_lucide=icon,
                class_="inline-block pr-2",
                aria_hidden="true",
            ),
            name,
        ],
        div(class_="min-w-0 text-base-text")[value],
    ]
