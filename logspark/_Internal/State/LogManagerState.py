import logging
from dataclasses import dataclass


@dataclass
class LogManagerState:
    """State management for a LogManager instance"""

    managed_loggers: dict[str, logging.Logger]

    def __post_init__(self) -> None:
        if getattr(self, "managed_loggers", None) is None:
            self.managed_loggers = {}
