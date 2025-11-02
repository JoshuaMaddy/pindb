from htpy import Element, div, i, p


def icon_list_item(icon: str, name: str, value: str) -> Element:
    return div(class_="flex flex-wrap gap-2 items-baseline")[
        p(class_="text-lg font-semibold")[
            i(
                data_lucide=icon,
                class_="inline-block pr-2",
            ),
            name,
        ],
        value,
    ]
