"""
htpy page and fragment builders: `templates/components/nav/pill_link.py`.
"""

from htpy import Element, a, i


def pill_link(
    href: str,
    text: str,
    icon: str | None = None,
    color_classes: str = "bg-main text-base-text border-lightest",
    hover_classes: str = "hover:border-accent hover:text-accent",
) -> Element:
    return a(
        href=href,
        class_=f"inline-flex items-center gap-1 px-2 py-1 rounded-lg border {color_classes} text-sm no-underline {hover_classes}",
    )[
        icon
        and i(
            data_lucide=icon, class_=f"w-3 h-3 shrink-0 {color_classes} {hover_classes}"
        ),
        text,
    ]
