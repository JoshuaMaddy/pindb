"""
htpy page and fragment builders: `templates/get/pin_collection.py`.
"""

from __future__ import annotations

from fastapi import Request
from htpy import Element, button, div, i, span
from markupsafe import Markup

from pindb.database.grade import Grade
from pindb.database.pin import Pin
from pindb.database.user_owned_pin import UserOwnedPin
from pindb.database.user_wanted_pin import UserWantedPin

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
    "absolute z-10 top-full mt-1 left-0 bg-main border border-lightest"
    " rounded-lg shadow-lg p-2 flex flex-col gap-1 text-sm"
)


def owned_panel(
    request: Request,
    pin: Pin,
    owned_entries: list[UserOwnedPin],
) -> Element:
    count: int = sum(entry.quantity for entry in owned_entries)
    return div(
        class_="relative",
        x_data=f"{{ open: false, count: {count} }}",
        **{"@owned-count-update": "count = $event.detail"},
    )[
        div(class_="contents", **{"@click": "open = !open"})[
            div(class_=_ACTION_BUTTON_CLASS)[
                i(data_lucide="package-check", class_="inline-block"),
                span(**{"x-text": "count > 0 ? `I Own (${count})` : 'I Own'"}),
            ],
        ],
        div(
            class_=f"{_PANEL_CLASS} min-w-[300px]",
            x_show="open",
            **{"@click.outside": "open = false"},
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

    return div(
        id=f"owned-panel-content-{pin.id}",
        class_="flex flex-col",
        x_init=f"$dispatch('owned-count-update', {sum(entry.quantity for entry in owned_entries)})",
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
) -> Markup:
    grade_name: str = grade.name if grade is not None else "Unknown"
    target_id: str = f"owned-panel-content-{pin_id}"

    if entry is not None:
        return _owned_row_existing(
            request=request,
            pin_id=pin_id,
            grade_name=grade_name,
            target_id=target_id,
            entry=entry,
        )

    grade_id: int | None = grade.id if grade is not None else None
    return _owned_row_new(
        request=request,
        pin_id=pin_id,
        grade_id=grade_id,
        grade_name=grade_name,
        target_id=target_id,
    )


def _owned_row_existing(
    request: Request,
    pin_id: int,
    grade_name: str,
    target_id: str,
    entry: UserOwnedPin,
) -> Markup:
    patch_url: str = str(
        request.url_for("update_owned_pin", pin_id=pin_id, entry_id=entry.id)
    )
    delete_url: str = str(
        request.url_for("remove_owned_pin", pin_id=pin_id, entry_id=entry.id)
    )
    is_tradeable: str = "true" if entry.tradeable_quantity > 0 else "false"
    tradeable_qty: int = entry.tradeable_quantity if entry.tradeable_quantity > 0 else 1
    safe_grade_name: Markup = Markup.escape(grade_name)

    return Markup(
        f"""<div class="flex items-center gap-2 py-1.5 px-1 border-b border-lightest last:border-0"
             x-data="{{ tradeable: {is_tradeable}, tradeable_qty: {tradeable_qty}, max_qty: {entry.quantity} }}">
          <span class="w-20 text-sm shrink-0">{safe_grade_name}</span>
          <input type="number" value="{entry.quantity}" min="1"
                 class="w-14 text-sm bg-lighter border border-lightest rounded px-1 py-0.5"
                 title="Quantity owned"
                 @change="max_qty = Math.max(1, parseInt($el.value) || 1); tradeable_qty = Math.min(tradeable_qty, max_qty); htmx.ajax('PATCH', '{patch_url}', {{target: '#{target_id}', swap: 'outerHTML', values: {{quantity: max_qty, tradeable_quantity: tradeable ? tradeable_qty : 0}}}})">
          <label class="flex items-center gap-1 text-sm cursor-pointer select-none shrink-0">
            <input type="checkbox" x-model="tradeable"
                   @change="htmx.ajax('PATCH', '{patch_url}', {{target: '#{target_id}', swap: 'outerHTML', values: {{quantity: max_qty, tradeable_quantity: tradeable ? tradeable_qty : 0}}}})">
            Trade
          </label>
          <input type="number" x-show="tradeable" x-model.number="tradeable_qty"
                 :min="1" :max="max_qty"
                 class="w-14 text-sm bg-lighter border border-lightest rounded px-1 py-0.5"
                 title="Quantity tradeable"
                 @change="tradeable_qty = Math.min(Math.max(1, parseInt($el.value) || 1), max_qty); htmx.ajax('PATCH', '{patch_url}', {{target: '#{target_id}', swap: 'outerHTML', values: {{quantity: max_qty, tradeable_quantity: tradeable_qty}}}})">
          <button type="button"
                  class="ml-auto shrink-0 text-lightest-hover hover:text-error-main-hover cursor-pointer bg-transparent border-0 text-lg leading-none"
                  aria-label="Remove from collection"
                  hx-delete="{delete_url}"
                  hx-target="#{target_id}"
                  hx-swap="outerHTML">×</button>
        </div>"""
    )


def _owned_row_new(
    request: Request,
    pin_id: int,
    grade_id: int | None,
    grade_name: str,
    target_id: str,
) -> Markup:
    add_url: str = str(request.url_for("add_owned_pin", pin_id=pin_id))
    grade_input: str = (
        f'<input type="hidden" name="grade_id" value="{grade_id}">'
        if grade_id is not None
        else ""
    )
    safe_grade_name: Markup = Markup.escape(grade_name)

    return Markup(
        f"""<div class="flex items-center gap-2 py-1.5 px-1 border-b border-lightest last:border-0">
          <span class="w-20 text-sm shrink-0 text-lightest-hover">{safe_grade_name}</span>
          <form hx-post="{add_url}" hx-target="#{target_id}" hx-swap="outerHTML" class="contents" data-htmx-submit-guard>
            {grade_input}
            <input type="number" name="quantity" value="1" min="1"
                   class="w-14 text-sm bg-lighter border border-lightest rounded px-1 py-0.5"
                   title="Quantity to add">
            <button type="submit"
                    class="text-sm text-accent hover:underline cursor-pointer bg-transparent border-0 p-0 shrink-0">
              + Add
            </button>
          </form>
        </div>"""
    )


# ---------------------------------------------------------------------------
# "I Want" panel
# ---------------------------------------------------------------------------


def wanted_panel(
    request: Request,
    pin: Pin,
    wanted_entries: list[UserWantedPin],
) -> Element:
    count: int = len(wanted_entries)
    return div(
        class_="relative",
        x_data=f"{{ open: false, count: {count} }}",
        **{"@wanted-count-update": "count = $event.detail"},
    )[
        div(class_="contents", **{"@click": "open = !open"})[
            div(class_=_ACTION_BUTTON_CLASS)[
                i(data_lucide="star", class_="inline-block"),
                span(**{"x-text": "count > 0 ? `I Want (${count})` : 'I Want'"}),
            ],
        ],
        div(
            class_=f"{_PANEL_CLASS} min-w-[200px]",
            x_show="open",
            **{"@click.outside": "open = false"},
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
        x_init=f"$dispatch('wanted-count-update', {len(wanted_entries)})",
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
