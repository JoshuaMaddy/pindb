"""Parse and validate physical dimensions (pin width/height) as text fields.

Dimensions are entered as a number plus a unit (``mm``, ``cm``, ``in``, …) and
stored or compared in millimeters elsewhere in the app.
"""

import re

# Unit token (regex group 2; group 1 is the number) — keep in sync with magnitude_to_mm.
_MAGNITUDE_UNIT_CAPTURE = r"(([Ii]nch(?:es)?)|(in)|(IN)|([Cc]entimeters?)|(cm)|(CM)|([Mm]illimeters?)|(mm)|(MM))"

# Numeric part: integer, decimal, or leading-dot decimal (e.g. .5in).
_MAGNITUDE_NUMBER_CAPTURE = r"(\d+(?:\.\d*)?|\.\d+)"

# For HTML5 `<input pattern="...">`: the value is trimmed, then matched as the entire string.
MAGNITUDE_INPUT_PATTERN = _MAGNITUDE_NUMBER_CAPTURE + r"\s*" + _MAGNITUDE_UNIT_CAPTURE

# Python: validate / parse a stripped dimension string end-to-end.
MAGNITUDE_FULLMATCH_PATTERN = r"^" + MAGNITUDE_INPUT_PATTERN + r"$"

# Backward-compatible name — same as MAGNITUDE_INPUT_PATTERN.
MAGNITUDE_PATTERN = MAGNITUDE_INPUT_PATTERN


def magnitude_is_valid(text: str) -> bool:
    """Return whether *text* is blank or a single ``number + unit`` magnitude.

    Args:
        text (str): Raw user input.

    Returns:
        bool: ``True`` for empty/whitespace-only input or a string matching
            ``MAGNITUDE_FULLMATCH_PATTERN``.
    """
    stripped = text.strip()
    if not stripped:
        return True
    return re.fullmatch(MAGNITUDE_FULLMATCH_PATTERN, stripped) is not None


class MagnitudeParseError(ValueError):
    """Raised when non-blank dimension text does not match the magnitude format."""


def parse_magnitude_mm(field_label: str, raw: str | None) -> float | None:
    """Return a width/height in millimeters, or ``None`` when unset.

    Args:
        field_label (str): Field name used in error messages (e.g. ``"Width"``).
        raw (str | None): Raw form value.

    Returns:
        float | None: Size in millimeters, or ``None`` when *raw* is missing
            or blank.

    Raises:
        MagnitudeParseError: When *raw* is non-blank but not a valid magnitude.
    """
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped:
        return None
    if not magnitude_is_valid(stripped):
        raise MagnitudeParseError(
            f"Invalid {field_label}: use a number with a unit (mm, cm, in, …). "
            "Examples: 40mm, 1.5in, 2 cm."
        )
    return magnitude_to_mm(stripped)


def empty_str_to_none(value: str | None) -> str | None:
    """Normalize empty strings to ``None`` for optional form fields.

    Args:
        value (str | None): Raw field value.

    Returns:
        str | None: ``None`` when *value* is ``None`` or ``""``, else *value*.
    """
    if value is None:
        return None
    if value == "":
        return None
    return value


def empty_str_list_to_none(values: list[str] | None) -> list[str] | None:
    """Drop blank strings from a list; return ``None`` if nothing remains.

    Args:
        values (list[str] | None): List from a multi-value form field.

    Returns:
        list[str] | None: Non-empty strings, or ``None`` when *values* is
            ``None`` or all entries are blank.
    """
    if values is None:
        return None
    filtered: list[str] = [item for item in values if item != ""]
    if not filtered:
        return None
    return filtered


def magnitude_to_mm(magnitude: str) -> float:
    """Convert a validated magnitude string to millimeters.

    Args:
        magnitude (str): Non-blank string matching ``MAGNITUDE_FULLMATCH_PATTERN``
            when trimmed; blank strings yield ``0``.

    Returns:
        float: Length in millimeters, or ``0`` when *magnitude* is blank or
            parsing fails to match (should not occur after ``magnitude_is_valid``).
    """
    stripped = magnitude.strip()
    if not stripped:
        return 0
    match: re.Match[str] | None = re.fullmatch(MAGNITUDE_FULLMATCH_PATTERN, stripped)
    if not match:
        return 0
    magnitude_float = float(match.group(1))
    unit_token: str = match.group(2).lower()

    if "inches".startswith(unit_token):
        return magnitude_float * 25.4
    if unit_token in ["centimeters", "cm"]:
        return magnitude_float * 10
    if unit_token in ["millimeters", "mm"]:
        return magnitude_float
    return 0
