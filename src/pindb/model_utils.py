import re
from typing import Any

MAGNITUDE_PATTERN = r".*?(\d*\.?\d*)\s*(([Ii]nch(?:es)?)|(in)|(IN)|([Cc]entimeters?)|(cm)|(CM)|([Mm]illimeters?)|(mm)|(MM))"


def empty_str_to_none(v: str | None) -> str | None:
    if v is None:
        return None
    if v == "":
        return None
    return v


def empty_str_list_to_none(v: list[Any] | None) -> list[Any] | None:
    if v is None:
        return None
    if len(v) == 1 and v[0] == "":
        return None
    else:
        return v


def magnitude_to_mm(magnitude: str) -> float:
    match = re.match(MAGNITUDE_PATTERN, magnitude)

    if not match:
        return 0

    magnitude_float = float(match.group(1))
    unit = match.group(2).lower()

    if "inches".startswith(unit):
        return magnitude_float * 25.4
    elif unit in ["centimeters", "cm"]:
        return magnitude_float * 10
    elif unit in ["millimeters", "mm"]:
        return magnitude_float
    else:
        return 0
