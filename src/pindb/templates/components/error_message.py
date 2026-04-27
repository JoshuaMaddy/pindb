"""
htpy page and fragment builders: `templates/components/error_message.py`.
"""

from htpy import Element, p


def error_message(error: str | None) -> Element | None:
    """Red error paragraph for form validation messages; returns None when there is no error."""
    if not error:
        return None
    return p(class_="text-error-main")[error]
