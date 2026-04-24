"""
Descriptive ``alt`` strings for pin photographs in templates.
"""

from pindb.database.pin import Pin


def _pin_display_name(pin: Pin) -> str:
    return f"(P) {pin.name}" if pin.is_pending else pin.name


def pin_front_image_alt(pin: Pin) -> str:
    """Alt text for a pin's front (or only) image."""
    return f"Image of pin {_pin_display_name(pin)}"


def pin_back_image_alt(pin: Pin) -> str:
    """Alt text for a pin's back image."""
    return f"Back image of pin {_pin_display_name(pin)}"
