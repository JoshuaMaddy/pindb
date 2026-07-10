"""UI-driven helpers for PinDB's enhanced select widgets.

Specs drive the widgets through real clicks and keystrokes only, so the same
spec passes against the legacy Tom Select controls and the native Svelte
MultiSelect component (lockstep protocol). Never reach into widget JS
internals from a spec — the widget implementation is exactly what these
helpers abstract over.

All helpers take the underlying ``<select>`` locator. Both implementations
keep that element in the DOM and in sync (that is what the form submits), so
value assertions read it directly. The visible widget is resolved from it:

- Legacy Tom Select renders a ``.ts-wrapper`` sibling immediately after the
  select; the dropdown is ``.ts-dropdown`` (possibly parented to ``body``).
- The native component owns its select inside a ``[data-multiselect]`` root,
  with ``[data-ms-control]`` and ``[data-ms-dropdown]`` hooks and
  ``[data-selectable]``/``[data-value]`` on options and chips.
"""

from __future__ import annotations

import re
import time

from playwright.sync_api import Locator, Page, expect

_DROPDOWN = ".ts-dropdown:visible, [data-ms-dropdown]:visible"
_CONTROL = ".ts-control, [data-ms-control]"
_OPTION = "[data-selectable]:not(.create):not([data-ms-create])"
_CREATE_OPTION = "[data-selectable].create, [data-selectable][data-ms-create]"


def widget_root(select: Locator) -> Locator:
    """Visible widget for *select*, whichever implementation is live."""
    native = select.locator("xpath=ancestor::*[@data-multiselect][1]")
    legacy = select.locator(
        "xpath=following-sibling::*[contains(@class, 'ts-wrapper')][1]"
    )
    return native.or_(legacy)


def control_items(select: Locator) -> Locator:
    """Selected chips/items rendered inside the widget control."""
    return widget_root(select).locator(_CONTROL).first.locator("[data-value]")


def _open(page: Page, select: Locator) -> Locator:
    root = widget_root(select)
    expect(root).to_be_visible()
    root.locator(_CONTROL).first.click()
    return root


def _dropdown(page: Page) -> Locator:
    return page.locator(_DROPDOWN).first


def multi_add(
    page: Page,
    select: Locator,
    query: str,
    *,
    option_text: str | re.Pattern[str] | None = None,
    option_exact: bool = False,
    create: bool = False,
    timeout: float = 10_000,
) -> None:
    """Open the widget, type *query*, and pick the matching option.

    With ``create=True`` picks the "Add …" create option instead of an
    existing entry. ``option_text`` overrides the text matched in the
    dropdown (defaults to *query* — remote loads may take a moment, which
    the visibility wait absorbs); pass a compiled pattern for full control.
    ``option_exact=True`` matches the whole option text (case-insensitive)
    instead of a substring — use it when one option's text is a prefix of
    another's.
    """
    root = _open(page, select)
    search = root.locator("input[type='text']").first
    # Real keystrokes: both implementations react to key events (filtering,
    # remote-load debounce), which a programmatic value set can bypass.
    search.press_sequentially(query, delay=20)
    dropdown = _dropdown(page)
    if create:
        option = dropdown.locator(_CREATE_OPTION).filter(has_text=f"Add {query}").first
    else:
        wanted: str | re.Pattern[str] = option_text or query
        if option_exact and isinstance(wanted, str):
            wanted = re.compile(rf"^\s*{re.escape(wanted)}\s*$", re.I)
        option = dropdown.locator(_OPTION).filter(has_text=wanted).first
    try:
        expect(option).to_be_visible(timeout=timeout)
    except AssertionError as exc:
        raise AssertionError(
            f"option for query {query!r} (text={option_text or query!r}) never "
            f"appeared; dropdown html: {_dropdown_debug(page)}"
        ) from exc
    option.click()
    page.keyboard.press("Escape")


def _dropdown_debug(page: Page) -> str:
    dropdown = page.locator(_DROPDOWN)
    if dropdown.count() == 0:
        return "<no visible dropdown>"
    return dropdown.first.inner_html()[:1000]


def single_pick(
    page: Page,
    select: Locator,
    option_text: str,
    *,
    timeout: float = 10_000,
) -> None:
    """Open a single-select widget and choose the option with *option_text*."""
    _open(page, select)
    option = _dropdown(page).locator(_OPTION).filter(has_text=option_text).first
    expect(option).to_be_visible(timeout=timeout)
    option.click()


def expect_option_available(
    page: Page,
    select: Locator,
    query: str,
    *,
    option_text: str | None = None,
    timeout: float = 10_000,
) -> None:
    """Assert an option is offered for *query*, then close the dropdown."""
    root = _open(page, select)
    if query:
        root.locator("input[type='text']").first.press_sequentially(query, delay=20)
    option = (
        _dropdown(page).locator(_OPTION).filter(has_text=option_text or query).first
    )
    expect(option).to_be_visible(timeout=timeout)
    page.keyboard.press("Escape")


def selected_values(select: Locator) -> list[str]:
    """Values currently selected on the underlying ``<select>``."""
    return select.evaluate(
        "el => Array.from(el.selectedOptions).map(option => option.value)"
    )


def wait_for_option_indexed(
    page: Page,
    options_url: str,
    name: str,
    *,
    timeout_s: float = 30.0,
) -> None:
    """Poll a select options endpoint until *name* appears (Meili sync lag).

    ``options_url`` is the full endpoint URL (e.g. read from the page's ref
    JSON or a ``data-options-url`` attribute), without the ``q`` param.
    """
    separator = "&" if "?" in options_url else "?"
    url = f"{options_url}{separator}q={name}"
    deadline = time.time() + timeout_s
    last: str = "<no response>"

    def _norm(value: str) -> str:
        # Display texts titlecase and swap underscores for spaces
        # (e.g. tag "img_tag" renders as "Img Tag").
        return value.lower().replace("_", " ")

    while time.time() < deadline:
        response = page.request.get(url)
        last = f"{response.status}: {response.text()[:300]}"
        if response.ok and any(
            _norm(name) in _norm(option["text"])
            or _norm(name) == _norm(str(option.get("value", "")))
            for option in response.json()
        ):
            return
        time.sleep(0.25)
    raise AssertionError(f"option {name!r} not indexed at {options_url}; last={last!r}")
