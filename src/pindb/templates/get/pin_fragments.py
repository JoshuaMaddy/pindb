"""
htpy page and fragment builders: `templates/get/pin_fragments.py`.

Reusable HTMX fragments returned both by the pin page and by toggle
endpoints in routes (favorite / set membership). Lives in its own module
so route handlers and the pin details builder can both import without
pulling in the whole page.
"""

from fastapi import Request
from htpy import Element, div, i

from pindb.database.pin_set import PinSet
from pindb.templates.components.toggle_button import toggle_button


def favorite_button(request: Request, pin_id: int, is_favorited: bool) -> Element:
    icon_fill = "fill-red-400 stroke-red-400" if is_favorited else ""
    label_text = "Unfavorite" if is_favorited else "Favorite"
    action_url = str(
        request.url_for(
            "unfavorite_pin" if is_favorited else "favorite_pin",
            pin_id=pin_id,
        )
    )
    return div(id=f"favorite-btn-{pin_id}")[
        toggle_button(
            url=action_url,
            is_active=is_favorited,
            target_id=f"favorite-btn-{pin_id}",
            children=[
                i(data_lucide="heart", class_=f"inline-block {icon_fill}".strip()),
                label_text,
            ],
            class_="flex items-center gap-1 px-2 py-1 rounded-lg border border-lightest bg-lighter hover:border-accent cursor-pointer text-base-text",
        )
    ]


def set_row(
    request: Request,
    pin_id: int,
    pin_set: PinSet,
    in_set: bool,
) -> Element:
    """Single row in the add-to-set dropdown. Returned by HTMX toggle endpoints."""
    action_url = str(
        request.url_for(
            "remove_pin_from_personal_set" if in_set else "add_pin_to_personal_set",
            set_id=pin_set.id,
            pin_id=pin_id,
        )
    )
    return div(id=f"set-row-{pin_set.id}-{pin_id}")[
        toggle_button(
            url=action_url,
            is_active=in_set,
            target_id=f"set-row-{pin_set.id}-{pin_id}",
            children=[
                i(
                    data_lucide="check-square" if in_set else "square",
                    class_="inline-block shrink-0",
                ),
                pin_set.name,
            ],
            class_="w-full flex items-center gap-2 px-2 py-1 rounded hover:bg-lighter-hover cursor-pointer text-base-text bg-transparent border-0 text-left font-inherit",
        )
    ]
