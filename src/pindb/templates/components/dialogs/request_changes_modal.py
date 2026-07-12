"""
htpy page and fragment builders: `templates/components/dialogs/request_changes_modal.py`.
"""

from htpy import Element

from pindb.templates.components.islands import island


def request_changes_modal(
    *,
    trigger: Element,
    form_action: str,
    entity_label: str,
    min_length: int,
    hx_target: str = "#pending-content",
    hx_swap: str = "outerHTML",
) -> Element:
    """Wrap *trigger* in the change-request dialog (Svelte ``request-changes-modal``).

    The dialog collects the reviewer's explanation and POSTs it to *form_action*,
    which must be one of the ``/admin/pending/reject*`` routes. Its submit button
    stays disabled until the reason reaches *min_length* characters; that gate is
    UX only, and ``routes/approve.py`` re-validates the length.
    """
    return island(
        "request-changes-modal",
        props={
            "triggerHtml": str(trigger),
            "formAction": form_action,
            "entityLabel": entity_label,
            "minLength": min_length,
            "hxTarget": hx_target,
            "hxSwap": hx_swap,
        },
        class_="inline-flex items-center self-center",
    )
