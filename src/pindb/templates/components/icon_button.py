from htpy import Element, a, button, i


def icon_button(
    icon: str,
    title: str,
    href: str | None = None,
    variant: str = "default",
) -> Element:
    """Icon-only button or link with a tooltip title.

    variant: "default" | "danger"
    Pass href to render an <a>, otherwise renders a <button type="button">.
    Extra kwargs are forwarded as attributes (e.g. hx_delete, hx_target).
    """
    color = (
        "text-red-400 hover:border-red-400"
        if variant == "danger"
        else "text-pin-base-text hover:border-accent"
    )
    base_class = (
        f"flex items-center justify-center p-1.5 rounded border border-pin-base-400 "
        f"bg-transparent cursor-pointer {color}"
    )

    icon_el: Element = i(data_lucide=icon, class_="w-4 h-4")

    if href is not None:
        return a(
            href=href,
            title=title,
            class_=base_class,
        )[icon_el]

    return button(
        type_="button",
        title=title,
        class_=base_class,
    )[icon_el]
