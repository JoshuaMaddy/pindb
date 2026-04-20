"""
htpy page and fragment builders: `templates/components/view_toggle.py`.
"""

from urllib.parse import urlencode

from htpy import Element, a, div

from pindb.models.list_view import EntityListView

_ACTIVE_CLASS: str = (
    "px-3 py-1 rounded border border-accent text-accent text-sm no-underline"
)
_INACTIVE_CLASS: str = (
    "px-3 py-1 rounded border border-pin-base-400 text-pin-base-300 text-sm "
    "hover:border-accent no-underline"
)


def view_toggle(
    base_url: str,
    current_view: EntityListView,
    section_id: str,
    extra_params: dict[str, str] | None = None,
) -> Element:
    def _link(label: str, view: EntityListView) -> Element:
        is_active: bool = current_view == view
        params: dict[str, str] = {"view": view.value, "page": "1"}
        if extra_params:
            params.update(extra_params)
        href: str = f"{base_url}?{urlencode(params)}"
        return a(
            href=href,
            hx_get=href,
            hx_target=f"#{section_id}",
            hx_swap="outerHTML",
            hx_push_url="true",
            class_=_ACTIVE_CLASS if is_active else _INACTIVE_CLASS,
        )[label]

    return div(class_="flex gap-2")[
        _link(label="Grid", view=EntityListView.grid),
        _link(label="Detailed", view=EntityListView.detailed),
    ]
