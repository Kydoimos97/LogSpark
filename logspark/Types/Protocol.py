from typing import Protocol


class SupportsWrite(Protocol):
    # noinspection PyUnusedFunction
    def write(self, s: str, /) -> int: ...
