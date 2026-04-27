"""
htpy page and fragment builders: `templates/components/empty_state.py`.
"""

from htpy import Element, p


def empty_state(
    message: str = "Nothing here yet.",
    small: bool = False,
) -> Element:
    """Muted paragraph for empty list/section states."""
    classes = "text-lightest-hover text-sm" if small else "text-lightest-hover"
    return p(class_=classes)[message]
