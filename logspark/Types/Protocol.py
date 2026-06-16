import logging
from typing import Protocol


class SupportsWrite(Protocol):
    # noinspection PyUnusedFunction
    def write(self, s: str, /) -> int: ...


class SupportsFilter(Protocol):
    def filter(self, record: logging.LogRecord, /) -> bool: ...
