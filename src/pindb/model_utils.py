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


def magnitude_is_valid(s: str) -> bool:
    """True if *s* is empty/whitespace-only, or a single magnitude string (number + unit)."""
    t = s.strip()
    if not t:
        return True
    return re.fullmatch(MAGNITUDE_FULLMATCH_PATTERN, t) is not None


class MagnitudeParseError(ValueError):
    """Non-empty dimension text did not match the accepted magnitude format."""


def parse_magnitude_mm(field_label: str, raw: str | None) -> float | None:
    """Return width/height in millimeters, or *None* if unset/blank.

    Raises *MagnitudeParseError* if *raw* is non-blank but not a valid magnitude string.
    """
    if raw is None:
        return None
    t = raw.strip()
    if not t:
        return None
    if not magnitude_is_valid(t):
        raise MagnitudeParseError(
            f"Invalid {field_label}: use a number with a unit (mm, cm, in, …). "
            "Examples: 40mm, 1.5in, 2 cm."
        )
    return magnitude_to_mm(t)


def empty_str_to_none(v: str | None) -> str | None:
    if v is None:
        return None
    if v == "":
        return None
    return v


def empty_str_list_to_none(v: list[str] | None) -> list[str] | None:
    if v is None:
        return None
    filtered: list[str] = [item for item in v if item != ""]
    if not filtered:
        return None
    return filtered


def magnitude_to_mm(magnitude: str) -> float:
    t = magnitude.strip()
    if not t:
        return 0
    match: re.Match[str] | None = re.fullmatch(MAGNITUDE_FULLMATCH_PATTERN, t)
    if not match:
        return 0
    magnitude_float = float(match.group(1))
    unit: str = match.group(2).lower()

    if "inches".startswith(unit):
        return magnitude_float * 25.4
    elif unit in ["centimeters", "cm"]:
        return magnitude_float * 10
    elif unit in ["millimeters", "mm"]:
        return magnitude_float
    else:
        return 0
