from htpy import Element, p


def empty_state(
    message: str = "Nothing here yet.",
    small: bool = False,
) -> Element:
    """Muted paragraph for empty list/section states."""
    classes = "text-pin-base-300 text-sm" if small else "text-pin-base-300"
    return p(class_=classes)[message]
