"""
htpy page and fragment builders: `templates/components/icon_list_element.py`.
"""

from htpy import Element, div, i, p


def icon_list_item(
    icon: str,
    name: str,
    value: str,
) -> Element:
    return div(class_="flex flex-wrap gap-2 items-baseline")[
        p(class_="text-base font-semibold sm:text-lg")[
            i(
                data_lucide=icon,
                class_="inline-block pr-2",
            ),
            name,
        ],
        value,
    ]
