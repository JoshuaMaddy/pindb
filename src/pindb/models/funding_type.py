from enum import StrEnum, auto


class FundingType(StrEnum):
    self = auto()
    crowdfunded = auto()
    sponsored = auto()
