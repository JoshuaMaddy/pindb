"""
htpy page and fragment builders: `templates/components/dialogs/confirm_modal.py`.
"""

from htpy import Element

from pindb.templates.components.islands import island


def confirm_modal(
    trigger: Element,
    message: str,
    form_action: str | None = None,
    hx_delete: str | None = None,
    hx_target: str | None = None,
    hx_swap: str = "outerHTML",
    confirm_label: str = "Delete",
    *,
    htmx_post: bool = False,
) -> Element:
    """Wrap *trigger* in a confirmation modal (Svelte ``confirm-modal`` island).

    Exactly one of form_action or hx_delete must be supplied:
    - form_action: fires a POST <form> when confirmed (full page redirect).
    - hx_delete:   fires an HTMX DELETE request when confirmed (partial swap).
    - htmx_post:   with form_action, submit via HTMX (``hx-post`` / ``hx-swap:
      none``) so the server can respond with ``HX-Redirect`` and ``HX-Trigger``
      toasts.
    """
    if form_action is None and hx_delete is None:
        raise ValueError("confirm_modal requires either form_action or hx_delete")

    return island(
        "confirm-modal",
        props={
            "triggerHtml": str(trigger),
            "message": message,
            "formAction": form_action or "",
            "hxDelete": hx_delete or "",
            "hxTarget": hx_target or "",
            "hxSwap": hx_swap,
            "confirmLabel": confirm_label,
            "htmxPost": htmx_post,
        },
        class_="inline-flex items-center self-center",
    )
