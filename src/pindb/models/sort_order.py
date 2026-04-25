"""Sort options for entity list pages."""

from enum import StrEnum, auto


class SortOrder(StrEnum):
    name = auto()
    newest = auto()
    oldest = auto()
