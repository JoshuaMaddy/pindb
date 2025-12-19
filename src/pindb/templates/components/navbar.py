from htpy import Element, a, nav


def navbar() -> Element:
    return nav(class_="flex gap-4 px-2 py-1 bg-pin-base-500")[
        a(class_="no-underline text-accent font-bold", href="/")["PinDB"],
        a(class_="no-underline text-pin-base-100", href="/create")["Create"],
        a(class_="no-underline text-pin-base-100", href="/list")["List"],
        a(class_="no-underline text-pin-base-100", href="/search/pin")["Search Pin"],
    ]
