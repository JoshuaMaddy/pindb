from htpy import Element, a, i


def back_link() -> Element:
    return a(id="back-link")[
        i(
            data_lucide="chevron-left",
            class_="inline-block",
        ),
        "Back",
    ]
