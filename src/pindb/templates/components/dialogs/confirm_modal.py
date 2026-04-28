"""
htpy page and fragment builders: `templates/components/dialogs/confirm_modal.py`.
"""

from htpy import Element, button, div, form, i, p


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
    """Wrap *trigger* in an Alpine.js confirmation modal.

    Exactly one of form_action or hx_delete must be supplied:
    - form_action: fires a POST <form> when confirmed (full page redirect).
    - hx_delete:   fires an HTMX DELETE request when confirmed (partial swap).
    - htmx_post:   with form_action, submit via HTMX (``hx-post`` / ``hx-swap: none``)
      so the server can respond with ``HX-Redirect`` and ``HX-Trigger`` toasts.
    """
    if form_action is None and hx_delete is None:
        raise ValueError("confirm_modal requires either form_action or hx_delete")

    # Build the confirm button inside the modal
    confirm_btn_base_class = (
        "flex items-center gap-1 px-2 py-1 rounded border border-error-dark "
        "bg-transparent cursor-pointer text-error-main hover:bg-error-dark-hover"
    )

    if form_action is not None:
        form_attrs: dict[str, object] = {"method": "post", "action": form_action}
        if htmx_post:
            form_attrs["hx_post"] = form_action
            form_attrs["hx_swap"] = "none"
        confirm_btn: Element = form(**form_attrs)[
            button(
                type="submit",
                class_=confirm_btn_base_class,
            )[confirm_label]
        ]
    else:
        htmx_attrs: dict[str, object] = {
            "hx_delete": hx_delete,
            "@click": "open = false",
        }
        if hx_target:
            htmx_attrs["hx_target"] = hx_target
        htmx_attrs["hx_swap"] = hx_swap
        confirm_btn: Element = button(
            type="button",
            class_=confirm_btn_base_class,
            **htmx_attrs,
        )[confirm_label]

    cancel_class = (
        "flex items-center gap-1 px-2 py-1 rounded border border-lightest "
        "bg-transparent cursor-pointer text-base-text hover:border-accent"
    )

    modal_overlay: Element = div(
        class_="fixed inset-0 z-50 flex items-center justify-center bg-darker/80",
        x_show="open",
        x_cloak=True,
        **{"@click.self": "open = false"},
    )[
        div(
            class_=(
                "relative bg-main border border-lightest rounded-xl "
                "shadow-2xl p-6 max-w-sm w-full mx-4 flex flex-col gap-4"
            ),
            **{"@click.stop": ""},
        )[
            # X close button
            button(
                type="button",
                class_=(
                    "absolute top-3 right-3 flex items-center justify-center "
                    "w-6 h-6 rounded border-0 bg-transparent cursor-pointer "
                    "text-lightest-hover hover:text-base-text"
                ),
                **{"@click": "open = false"},
            )[i(data_lucide="x", class_="w-4 h-4")],
            p(class_="text-base")[message],
            div(class_="flex gap-2 justify-end")[
                button(
                    type="button",
                    class_=cancel_class,
                    **{"@click": "open = false"},
                )["Cancel"],
                confirm_btn,
            ],
        ]
    ]

    return div(
        class_="inline-flex items-center self-center",
        x_data="{ open: false }",
    )[
        # Trigger — clicking it opens the modal
        div(class_="inline-flex items-center", **{"@click": "open = true"})[trigger],
        modal_overlay,
    ]
