from typing import NamedTuple, Tuple


class ColorTriplet(NamedTuple):
    red: int
    green: int
    blue: int

    @property
    def hex(self) -> str:
        ...

    @property
    def rgb(self) -> str:
        ...

    @property
    def normalized(self) -> Tuple[float, float, float]:
        ...