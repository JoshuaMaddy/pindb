"""The navbar unread indicator dot — rendered by the navbar and re-emitted OOB.

A single stable ``#navbar-unread-dot`` element hosts the dot so message actions
can keep it in sync with an out-of-band swap without re-rendering the navbar.
"""

from __future__ import annotations

from htpy import Element, span

UNREAD_DOT_ID = "navbar-unread-dot"


def unread_dot(unread: bool, *, oob: bool = False) -> Element:
    """The unread indicator overlay for the mail icon.

    Always renders the wrapper (so the OOB target exists even when read); the
    coloured dot appears only when *unread*. Pass ``oob=True`` to return the
    same element flagged for an HTMX out-of-band swap.
    """
    attrs: dict[str, object] = {
        "id": UNREAD_DOT_ID,
        "class_": "absolute -top-1 -right-1 flex",
    }
    if oob:
        attrs["hx_swap_oob"] = "true"
    return span(**attrs)[
        unread
        and span(
            class_="block w-2.5 h-2.5 rounded-full bg-accent ring-2 ring-main",
        )[span(class_="sr-only")["Unread messages"]]
    ]
