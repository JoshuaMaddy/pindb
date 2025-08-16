from enum import StrEnum, auto


class AcquisitionType(StrEnum):
    single = auto()
    blind_box = auto()
    set = auto()
