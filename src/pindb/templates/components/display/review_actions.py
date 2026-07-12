"""
htpy page and fragment builders: `templates/components/display/review_actions.py`.

The approve / request-changes / delete controls, plus the admin review bar that
carries them on an entry's own detail page. The buttons live here rather than in
`templates/admin/` because both the pending queue and the detail pages render
them; `templates/admin/_pending_shared.py` re-exports them for the queue.
"""

from htpy import Element, button, div, form, fragment, i

from pindb.database.entity_type import EntityType
from pindb.database.pending_mixin import MIN_CHANGE_REQUEST_LENGTH
from pindb.templates.components.dialogs.confirm_modal import confirm_modal
from pindb.templates.components.dialogs.request_changes_modal import (
    request_changes_modal,
)

# action key -> (lucide icon, button variant class, default label)
_ACTION_SPECS: dict[str, tuple[str, str, str]] = {
    "approve": ("check", "btn-primary", "Approve"),
    "reject": ("message-square-warning", "btn-warning", "Request changes"),
    "delete": ("trash-2", "btn-error", "Delete"),
}

_BAR_CLASS: str = (
    "rounded bg-pending-dark border border-pending-dark text-pending-main "
    "px-4 py-2 text-sm my-2 flex flex-wrap items-center gap-x-4 gap-y-2 justify-between"
)


def _action_button(
    *,
    action: str,
    label: str | None = None,
    title: str | None = None,
    type_: str = "submit",
) -> Element:
    icon, variant, default_label = _ACTION_SPECS[action]
    text = label or default_label
    return button(type=type_, class_=f"btn btn-sm {variant}", title=title or text)[
        i(data_lucide=icon, class_="inline-block w-3 h-3 mr-1"),
        text,
    ]


def action_form_button(
    *,
    action: str,
    url: str,
    label: str | None = None,
    title: str | None = None,
    hx_target: str = "#pending-content",
    hx_swap: str = "outerHTML",
) -> Element:
    """A single POST form wrapping an icon button for an approve/reject/delete action.

    On the queue, ``hx-post`` swaps the whole ``#pending-content`` region in place so
    the queue updates without a full-page reload (which would reset the scroll
    position). A detail page has no queue to swap, so it passes ``hx_swap="none"``
    and the route answers with the history-back trigger instead.
    ``method``/``action`` remain as a no-JS fallback that redirects to the queue.
    """
    return form(
        method="post",
        action=url,
        hx_post=url,
        hx_target=hx_target,
        hx_swap=hx_swap,
    )[_action_button(action=action, label=label, title=title)]


def request_changes_button(
    *,
    url: str,
    entity_label: str,
    label: str | None = None,
    title: str | None = None,
    hx_target: str = "#pending-content",
    hx_swap: str = "outerHTML",
) -> Element:
    """The reject action, gated behind the change-request dialog.

    Unlike the other actions this one carries a body — the reviewer's explanation —
    so it cannot be a bare zero-input form. The dialog posts to the same
    ``/admin/pending/reject*`` route and swaps the same way.
    """
    return request_changes_modal(
        trigger=_action_button(action="reject", label=label, title=title),
        form_action=url,
        entity_label=entity_label,
        min_length=MIN_CHANGE_REQUEST_LENGTH,
        hx_target=hx_target,
        hx_swap=hx_swap,
    )


def action_buttons(*buttons: Element) -> Element:
    """Horizontal row wrapping the action buttons for one pending row/card."""
    return div(class_="flex gap-2")[list(buttons)]


def review_actions_bar(
    *,
    entity_type: EntityType,
    entity_id: int,
    entity_name: str,
    is_rejected: bool,
) -> Element:
    """Admin review controls on a pending entry's own detail page.

    The queue only lists an entry; an admin who wants to actually *look* at a
    submission before ruling on it ends up here, so the same three actions have to
    be reachable without navigating back. They post to the same ``/admin/pending/*``
    routes with ``?after=back``, which answers ``204`` plus an ``HX-Trigger`` that
    sends the admin one step back in history (see
    ``templates/js/shell/pindb_shell.js``) rather than swapping the queue fragment
    into this page.

    Mirrors the queue's needs-changes section: an entry already sent back offers
    Approve and Delete only — asking for changes a second time says nothing new.

    Callers gate on ``user.is_admin``; the routes re-check with ``require_admin``.
    """
    action_url = f"/admin/pending/{{}}/{entity_type.value}/{entity_id}?after=back"
    headline = (
        "Sent back for changes — waiting on the submitter."
        if is_rejected
        else "Awaiting review."
    )
    return div(class_=_BAR_CLASS)[
        div(class_="flex items-center gap-2 font-medium")[
            i(
                data_lucide="shield-check",
                class_="inline-block w-4 h-4 shrink-0",
                aria_hidden="true",
            ),
            headline,
        ],
        div(class_="flex gap-2")[
            action_form_button(
                action="approve",
                url=action_url.format("approve"),
                hx_target="this",
                hx_swap="none",
            ),
            fragment[
                not is_rejected
                and request_changes_button(
                    url=action_url.format("reject"),
                    entity_label=entity_name,
                    hx_target="this",
                    hx_swap="none",
                )
            ],
            confirm_modal(
                trigger=_action_button(action="delete", type_="button"),
                message=(
                    f'Delete "{entity_name}"? This deletes the entry, '
                    "not just the submission."
                ),
                form_action=action_url.format("delete"),
                htmx_post=True,
            ),
        ],
    ]
