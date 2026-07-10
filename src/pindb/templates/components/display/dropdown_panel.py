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
    """Disclosure: *trigger* toggles a floating *content* panel.

    Driven by the delegated ``data-disclosure`` handlers in
    ``templates/js/shell/pindb_shell.js`` (toggle via the ``hidden`` class,
    close on outside click / Escape). Prefer a ``button type="button"`` trigger
    with ``aria-haspopup="true"`` and ``aria-controls`` set to *panel_id*.
    """
    return div(class_="relative", data_disclosure=True)[
        div(class_="contents", data_disclosure_trigger=True)[trigger],
        div(
            id=panel_id,
            class_=f"hidden absolute z-10 top-full mt-1 left-0 {panel_class} bg-main border border-lightest rounded-lg shadow-lg p-2 flex-col gap-1 text-sm [&:not(.hidden)]:flex",
            data_disclosure_panel=True,
        )[content],
    ]
