import logging
from typing import Protocol, Optional


class SupportsWrite(Protocol):
    # noinspection PyUnusedFunction
    def write(self, s: str) -> Optional[int]: ...


class _SupportsFilter(Protocol):
    """Protocol for objects that support filtering LogRecords"""

    def filter(self, record: logging.LogRecord) -> bool: ...
