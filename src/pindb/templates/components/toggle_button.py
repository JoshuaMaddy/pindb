from htpy import Attribute, Element, Node, button


def toggle_button(
    url: str,
    is_active: bool,
    target_id: str,
    children: Node,
    swap: str = "outerHTML",
    **attrs: Attribute,
) -> Element:
    """Button that POSTs to *url* when inactive and DELETEs when active, swapping *target_id*."""
    return button(
        type_="button",
        hx_post=None if is_active else url,
        hx_delete=url if is_active else None,
        hx_target=f"#{target_id}",
        hx_swap=swap,
        **attrs,
    )[children]
