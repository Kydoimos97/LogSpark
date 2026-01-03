from enum import IntEnum
from typing import NamedTuple, Optional
from .color_triplet import ColorTriplet

class ColorType(IntEnum):
    """Type of color stored in Color class."""

    DEFAULT = 0
    STANDARD = 1
    EIGHT_BIT = 2
    TRUECOLOR = 3
    WINDOWS = 4

    def __repr__(self) -> str:
        return f"ColorType.{self.name}"


class Color(NamedTuple):
    name: str = ...
    type: ColorType = ...
    number: Optional[int] = ...
    triplet: Optional[ColorTriplet] = ...


