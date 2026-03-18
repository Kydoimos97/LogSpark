import logging
from typing import Protocol


class SupportsWrite(Protocol):
    # noinspection PyUnusedFunction
    def write(self, s: str) -> int | None: ...


# noinspection PyUnusedFunction
class _SupportsFilter(Protocol):
    """Protocol for objects that support filtering LogRecords"""

    def filter(self, record: logging.LogRecord) -> bool: ...


