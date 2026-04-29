"""
htpy page and fragment builders: `templates/components/layout/card.py`.
"""

from fastapi.datastructures import URL
from htpy import Element, a, div, i

from pindb.templates.components.layout.centered import Content

_CARD_BASE: str = (
    "p-2 no-underline text-base-text bg-main rounded-xl border border-lightest flex gap-2 "
    "cursor-pointer hover:scale-[102%] hover:border-accent hover:bg-main-hover "
    "transition-all duration-100 ease-linear"
)


def card(
    href: str | URL | None = None,
    icon: str | None = None,
    content: Content = None,
    additional_classes: str = "",
    *,
    wrap_in_anchor: bool = True,
) -> Element:
    """Clickable surface.

    With *href* and *wrap_in_anchor* true (default), renders a real ``<a>`` for
    keyboard focus and correct semantics.

    Set *wrap_in_anchor* false when *content* includes nested links or buttons
    (invalid inside ``<a>``); falls back to ``div`` + ``onclick`` like the legacy
    implementation.
    """
    parts: list[object] = []
    if icon:
        parts.append(
            i(
                data_lucide=icon,
                class_="inline-block shrink-0",
                aria_hidden="true",
            )
        )
    if content is not None:
        parts.append(content)

    class_: str = _CARD_BASE + (
        (" " + additional_classes) if additional_classes else ""
    )

    if href is not None and wrap_in_anchor:
        return a(href=str(href), class_=class_)[*parts]

    if href is not None:
        return div(
            onclick=f"window.location.href='{str(href)}'",
            class_=class_,
        )[*parts]

    return div(class_=class_)[*parts]
