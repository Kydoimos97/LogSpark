"""
Core data models for LogSpark Logging v2
"""

import logging
from dataclasses import dataclass

from ...Types import TracebackOptions


@dataclass(frozen=True)
class LoggerConfig:
    """
    Immutable configuration for LogSpark logger

    This represents pure input specification - freeze state belongs
    to logger lifecycle, not configuration.
    """

    level: int  # stdlib logging level (logging.INFO, etc.)
    fast_log: bool  # Performance optimization that trades correctness for speed
    handler: logging.Handler  # stdlib Handlers instance
    traceback_policy: TracebackOptions

    def __post_init__(self) -> None:
        """Validate configuration parameters"""
        if not isinstance(self.level, int):
            raise ValueError("level must be a stdlib logging level integer")

        if not isinstance(self.fast_log, bool):
            raise ValueError("fast_log must be a boolean")

        if not isinstance(self.handler, logging.Handler):
            raise ValueError("handler must be a stdlib logging.Handlers instance")

        if not isinstance(self.traceback_policy, TracebackOptions):
            raise ValueError("traceback_policy must be a TracebackOptions enum value")
