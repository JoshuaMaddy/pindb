from enum import StrEnum, auto


class AcquisitionType(StrEnum):
    single = auto()
    blind_box = auto()
    set = auto()

    def pretty_name(self) -> str:
        return self.name.capitalize().replace("_", " ")
