"""
htpy page and fragment builders: `templates/get/pin_collection.py`.
"""

from __future__ import annotations

from fastapi import Request
from htpy import Element, button, div, form, i, input, span

from pindb.database.grade import Grade
from pindb.database.pin import Pin
from pindb.database.user_owned_pin import UserOwnedPin
from pindb.database.user_wanted_pin import UserWantedPin
from pindb.templates.components.islands import island

_ACTION_BUTTON_CLASS = (
    "flex items-center gap-1 px-2 py-1 rounded-lg border border-lightest"
    " bg-lighter hover:border-accent cursor-pointer text-base-text"
)
_ROW_BUTTON_CLASS = (
    "w-full flex items-center gap-2 px-2 py-1 rounded hover:bg-lighter-hover"
    " cursor-pointer text-base-text bg-transparent border-0 text-left font-inherit"
)


# ---------------------------------------------------------------------------
# "I Own" panel
# ---------------------------------------------------------------------------


_PANEL_CLASS = (
    "hidden absolute z-10 top-full mt-1 left-0 bg-main border border-lightest"
    " rounded-lg shadow-lg p-2 flex-col gap-1 text-sm [&:not(.hidden)]:flex"
)


def _owned_label(count: int) -> str:
    return f"I Own ({count})" if count > 0 else "I Own"


def _wanted_label(count: int) -> str:
    return f"I Want ({count})" if count > 0 else "I Want"


def owned_panel(
    request: Request,
    pin: Pin,
    owned_entries: list[UserOwnedPin],
) -> Element:
    count: int = sum(entry.quantity for entry in owned_entries)
    return div(class_="relative", data_disclosure=True)[
        div(class_="contents", data_disclosure_trigger=True)[
            div(class_=_ACTION_BUTTON_CLASS)[
                i(data_lucide="package-check", class_="inline-block"),
                span(id=f"owned-count-label-{pin.id}")[_owned_label(count)],
            ],
        ],
        div(
            class_=f"{_PANEL_CLASS} min-w-[300px]",
            data_disclosure_panel=True,
        )[
            owned_panel_content(
                request=request,
                pin=pin,
                owned_entries=owned_entries,
            ),
        ],
    ]


def owned_panel_content(
    request: Request,
    pin: Pin,
    owned_entries: list[UserOwnedPin],
) -> Element:
    entry_by_grade_id: dict[int | None, UserOwnedPin] = {
        entry.grade_id: entry for entry in owned_entries
    }
    grades_sorted: list[Grade] = sorted(pin.grades, key=lambda grade: grade.name)
    count: int = sum(entry.quantity for entry in owned_entries)

    return div(
        id=f"owned-panel-content-{pin.id}",
        class_="flex flex-col",
        # pindb_shell.js applies this to the trigger label on load + afterSwap.
        data_count_for=f"owned-count-label-{pin.id}",
        data_count_text=_owned_label(count),
    )[
        [
            _owned_grade_row(
                request=request,
                pin_id=pin.id,
                grade=grade,
                entry=entry_by_grade_id.get(grade.id),
            )
            for grade in grades_sorted
        ],
        _owned_grade_row(
            request=request,
            pin_id=pin.id,
            grade=None,
            entry=entry_by_grade_id.get(None),
        ),
    ]


def _owned_grade_row(
    request: Request,
    pin_id: int,
    grade: Grade | None,
    entry: UserOwnedPin | None,
) -> Element:
    grade_name: str = grade.name if grade is not None else "Unknown"
    target_id: str = f"owned-panel-content-{pin_id}"

    if entry is not None:
        return island(
            "tradeable-row",
            props={
                "gradeName": grade_name,
                "quantity": entry.quantity,
                "tradeableQuantity": entry.tradeable_quantity,
                "patchUrl": str(
                    request.url_for(
                        "update_owned_pin", pin_id=pin_id, entry_id=entry.id
                    )
                ),
                "deleteUrl": str(
                    request.url_for(
                        "remove_owned_pin", pin_id=pin_id, entry_id=entry.id
                    )
                ),
                "targetId": target_id,
            },
        )

    grade_id: int | None = grade.id if grade is not None else None
    return _owned_row_new(
        request=request,
        pin_id=pin_id,
        grade_id=grade_id,
        grade_name=grade_name,
        target_id=target_id,
    )


def _owned_row_new(
    request: Request,
    pin_id: int,
    grade_id: int | None,
    grade_name: str,
    target_id: str,
) -> Element:
    add_url: str = str(request.url_for("add_owned_pin", pin_id=pin_id))
    return div(
        class_="flex items-center gap-2 py-1.5 px-1 border-b border-lightest last:border-0"
    )[
        span(class_="w-20 text-sm shrink-0 text-lightest-hover")[grade_name],
        form(
            hx_post=add_url,
            hx_target=f"#{target_id}",
            hx_swap="outerHTML",
            class_="contents",
            **{"data-htmx-submit-guard": ""},
        )[
            input(type="hidden", name="grade_id", value=str(grade_id))
            if grade_id is not None
            else "",
            input(
                type="number",
                name="quantity",
                value="1",
                min="1",
                class_="w-14 text-sm bg-lighter border border-lightest rounded px-1 py-0.5",
                title="Quantity to add",
            ),
            button(
                type="submit",
                class_="text-sm text-accent hover:underline cursor-pointer bg-transparent border-0 p-0 shrink-0",
            )["+ Add"],
        ],
    ]


# ---------------------------------------------------------------------------
# "I Want" panel
# ---------------------------------------------------------------------------


def wanted_panel(
    request: Request,
    pin: Pin,
    wanted_entries: list[UserWantedPin],
) -> Element:
    count: int = len(wanted_entries)
    return div(class_="relative", data_disclosure=True)[
        div(class_="contents", data_disclosure_trigger=True)[
            div(class_=_ACTION_BUTTON_CLASS)[
                i(data_lucide="star", class_="inline-block"),
                span(id=f"wanted-count-label-{pin.id}")[_wanted_label(count)],
            ],
        ],
        div(
            class_=f"{_PANEL_CLASS} min-w-[200px]",
            data_disclosure_panel=True,
        )[
            wanted_panel_content(
                request=request,
                pin=pin,
                wanted_entries=wanted_entries,
            ),
        ],
    ]


def wanted_panel_content(
    request: Request,
    pin: Pin,
    wanted_entries: list[UserWantedPin],
) -> Element:
    entry_by_grade_id: dict[int | None, UserWantedPin] = {
        entry.grade_id: entry for entry in wanted_entries
    }
    grades_sorted: list[Grade] = sorted(pin.grades, key=lambda grade: grade.name)

    return div(
        id=f"wanted-panel-content-{pin.id}",
        class_="flex flex-col",
        data_count_for=f"wanted-count-label-{pin.id}",
        data_count_text=_wanted_label(len(wanted_entries)),
    )[
        [
            _wanted_grade_row(
                request=request,
                pin_id=pin.id,
                grade=grade,
                entry=entry_by_grade_id.get(grade.id),
            )
            for grade in grades_sorted
        ],
        _wanted_grade_row(
            request=request,
            pin_id=pin.id,
            grade=None,
            entry=entry_by_grade_id.get(None),
        ),
    ]


def _wanted_grade_row(
    request: Request,
    pin_id: int,
    grade: Grade | None,
    entry: UserWantedPin | None,
) -> Element:
    grade_id: int | None = grade.id if grade is not None else None
    grade_name: str = grade.name if grade is not None else "Unknown"
    target_id: str = f"wanted-panel-content-{pin_id}"
    is_wanted: bool = entry is not None

    if is_wanted:
        assert entry is not None
        delete_url: str = str(
            request.url_for("remove_wanted_pin", pin_id=pin_id, entry_id=entry.id)
        )
        return button(
            type="button",
            hx_delete=delete_url,
            hx_target=f"#{target_id}",
            hx_swap="outerHTML",
            class_=_ROW_BUTTON_CLASS,
        )[
            i(
                data_lucide="check-square",
                class_="inline-block shrink-0",
                aria_hidden="true",
            ),
            grade_name,
        ]

    add_url: str = str(request.url_for("add_wanted_pin", pin_id=pin_id))
    grade_vals: str = f'{{"grade_id": {grade_id}}}' if grade_id is not None else "{}"
    return button(
        type="button",
        hx_post=add_url,
        hx_target=f"#{target_id}",
        hx_swap="outerHTML",
        hx_vals=grade_vals,
        class_=_ROW_BUTTON_CLASS,
    )[
        i(data_lucide="square", class_="inline-block shrink-0", aria_hidden="true"),
        grade_name,
    ]
