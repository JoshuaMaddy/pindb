"""
htpy page and fragment builders: `templates/components/display/dropdown_panel.py`.
"""

from htpy import BaseElement, Element, div

from pindb.templates.types import Content


def dropdown_panel(
    trigger: BaseElement,
    content: Content,
    panel_class: str = "min-w-[200px]",
    *,
    panel_id: str,
) -> Element:
    """Alpine-powered disclosure: *trigger* toggles a floating *content* panel.

    The *trigger* is wrapped in a div with ``@click="open = !open"`` (click
    bubbles from child controls, e.g. a ``<button>``). Prefer a ``button
    type="button"`` for focus and role, with ``:aria-expanded="open"``,
    ``aria-haspopup="true"``, and ``aria-controls`` set to *panel_id* on the
    same ``x-data`` root as this component.

    *panel_id* is the DOM ``id`` of the floating panel (for ``aria-controls``).
    Clicking outside the panel closes it via Alpine's ``@click.outside``.
    """
    return div(class_="relative", x_data="{ open: false }")[
        div(class_="contents", **{"@click": "open = !open"})[trigger],
        div(
            id=panel_id,
            class_=f"absolute z-10 top-full mt-1 left-0 {panel_class} bg-main border border-lightest rounded-lg shadow-lg p-2 flex flex-col gap-1 text-sm",
            x_show="open",
            **{"@click.outside": "open = false"},
        )[content],
    ]
