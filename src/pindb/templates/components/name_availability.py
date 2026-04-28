"""Shared HTMX wiring for debounced duplicate-name feedback."""

from __future__ import annotations

import json

from htpy import BaseElement, Element, div

NAME_AVAILABILITY_TRIGGER: str = "input changed delay:1s, search"


def name_check_attrs(
    *,
    check_url: str,
    kind: str,
    target_id: str,
    exclude_id: int | None = None,
) -> dict[str, str]:
    """Return HTMX attributes for a debounced name availability input."""
    values: dict[str, int | str] = {"kind": kind}
    if exclude_id is not None:
        values["exclude_id"] = exclude_id
    return {
        "hx_get": check_url,
        "hx_trigger": NAME_AVAILABILITY_TRIGGER,
        "hx_target": f"#{target_id}",
        "hx_swap": "innerHTML",
        "hx_vals": json.dumps(values),
    }


def name_availability_field(
    *,
    child: BaseElement,
    feedback_id: str = "name-availability-feedback",
    data_pin_field: str | None = None,
) -> Element:
    """Wrap a name input with the target container used for inline feedback."""
    wrapper_attrs: dict[str, str] = {}
    if data_pin_field is not None:
        wrapper_attrs["data_pin_field"] = data_pin_field
    return div(class_="name-availability-field flex flex-col gap-1", **wrapper_attrs)[
        child,
        div(
            id=feedback_id,
            class_="name-availability-feedback",
        ),
    ]
