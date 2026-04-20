"""How a pin was sold (single item, blind box, or set)."""

from enum import StrEnum, auto


class AcquisitionType(StrEnum):
    single = auto()
    blind_box = auto()
    set = auto()

    def pretty_name(self) -> str:
        """Human label for UI (title case, underscores to spaces)."""
        return self.name.capitalize().replace("_", " ")
