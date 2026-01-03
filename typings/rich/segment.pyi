from enum import IntEnum
from typing import (
    NamedTuple,
    Optional,
)

from .style import Style

class ControlType(IntEnum):
    ...

class Segment(NamedTuple):
    text: str
    style: Optional[Style] = None
    @property
    def cell_length(self) -> int: ...

