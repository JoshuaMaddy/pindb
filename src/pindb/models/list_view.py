"""User preference for entity browse pages (grid vs detailed)."""

from enum import StrEnum, auto


class EntityListView(StrEnum):
    grid = auto()
    detailed = auto()
