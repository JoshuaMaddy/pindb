"""
htpy page and fragment builders: `templates/components/dropdown_panel.py`.
"""

from htpy import BaseElement, Element, div

from pindb.templates.types import Content


def dropdown_panel(
    trigger: BaseElement,
    content: Content,
    panel_class: str = "min-w-[200px]",
) -> Element:
    """Alpine-powered dropdown: clicking *trigger* toggles a floating *content* panel.

    The trigger is wrapped in a div with ``@click="open = !open"``.
    Clicking outside the panel closes it via Alpine's ``@click.outside``.
    """
    return div(class_="relative", x_data="{ open: false }")[
        div(class_="contents", **{"@click": "open = !open"})[trigger],
        div(
            class_=f"absolute z-10 top-full mt-1 left-0 {panel_class} bg-pin-base-500 border border-pin-base-400 rounded-lg shadow-lg p-2 flex flex-col gap-1 text-sm",
            x_show="open",
            **{"@click.outside": "open = false"},
        )[content],
    ]
