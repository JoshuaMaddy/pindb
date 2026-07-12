"""
Descriptive ``alt`` strings for pin photographs in templates.
"""

from pindb.database.pin import Pin
from pindb.utils import review_label


def _pin_display_name(pin: Pin) -> str:
    return review_label(
        pin.name, is_pending=pin.is_pending, is_rejected=pin.is_rejected
    )


def pin_front_image_alt(pin: Pin) -> str:
    """Alt text for a pin's front (or only) image."""
    return f"Image of pin {_pin_display_name(pin)}"


def pin_back_image_alt(pin: Pin) -> str:
    """Alt text for a pin's back image."""
    return f"Back image of pin {_pin_display_name(pin)}"
