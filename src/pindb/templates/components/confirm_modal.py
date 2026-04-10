from htpy import Element, button, div, form, i, p


def confirm_modal(
    trigger: Element,
    message: str,
    form_action: str | None = None,
    hx_delete: str | None = None,
    hx_target: str | None = None,
    hx_swap: str = "outerHTML",
    confirm_label: str = "Delete",
) -> Element:
    """Wrap *trigger* in an Alpine.js confirmation modal.

    Exactly one of form_action or hx_delete must be supplied:
    - form_action: fires a POST <form> when confirmed (full page redirect).
    - hx_delete:   fires an HTMX DELETE request when confirmed (partial swap).
    """
    if form_action is None and hx_delete is None:
        raise ValueError("confirm_modal requires either form_action or hx_delete")

    # Build the confirm button inside the modal
    confirm_btn_base_class = (
        "flex items-center gap-1 px-3 py-1 rounded border border-red-400 "
        "bg-transparent cursor-pointer text-red-400 hover:bg-red-950/30"
    )

    if form_action is not None:
        confirm_btn: Element = form(method="post", action=form_action)[
            button(
                type_="submit",
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
            type_="button",
            class_=confirm_btn_base_class,
            **htmx_attrs,
        )[confirm_label]

    cancel_class = (
        "flex items-center gap-1 px-3 py-1 rounded border border-pin-base-400 "
        "bg-transparent cursor-pointer text-pin-base-text hover:border-accent"
    )

    modal_overlay: Element = div(
        class_="fixed inset-0 z-50 flex items-center justify-center bg-black/50",
        x_show="open",
        x_cloak=True,
        **{"@click.self": "open = false"},
    )[
        div(
            class_=(
                "relative bg-pin-base-500 border border-pin-base-400 rounded-xl "
                "shadow-2xl p-6 max-w-sm w-full mx-4 flex flex-col gap-4"
            ),
            **{"@click.stop": ""},
        )[
            # X close button
            button(
                type_="button",
                class_=(
                    "absolute top-3 right-3 flex items-center justify-center "
                    "w-6 h-6 rounded border-0 bg-transparent cursor-pointer "
                    "text-pin-base-300 hover:text-pin-base-text"
                ),
                **{"@click": "open = false"},
            )[i(data_lucide="x", class_="w-4 h-4")],
            p(class_="text-base")[message],
            div(class_="flex gap-2 justify-end")[
                button(
                    type_="button",
                    class_=cancel_class,
                    **{"@click": "open = false"},
                )["Cancel"],
                confirm_btn,
            ],
        ]
    ]

    return div(
        class_="relative",
        x_data="{ open: false }",
    )[
        # Trigger — clicking it opens the modal
        div(**{"@click": "open = true"})[trigger],
        modal_overlay,
    ]
