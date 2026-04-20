"""Optional funding model for a pin (self-funded, crowdfunding, sponsored)."""

from enum import StrEnum, auto


class FundingType(StrEnum):
    self = auto()
    crowdfunded = auto()
    sponsored = auto()
