"""
Core data models for LogSpark Logging v2
"""

import logging
from dataclasses import dataclass

from ...Types.Options import PathResolutionSetting, TracebackOptions


@dataclass(frozen=True)
class LoggerConfig:
    """
    Immutable configuration for LogSpark logger

    This represents pure input specification - freeze state belongs
    to logger lifecycle, not configuration.
    """

    level: int  # stdlib logging level (logging.INFO, etc.)
    handler: logging.Handler  # stdlib Handlers instance
    traceback_policy: TracebackOptions | None
    path_resolution: PathResolutionSetting | None

    def __post_init__(self) -> None:
        """Validate configuration parameters"""
        if not isinstance(self.level, int):
            raise ValueError("level must be a stdlib logging level integer")

        if not isinstance(self.handler, logging.Handler):
            raise ValueError("handler must be a stdlib logging.Handlers instance")

        if (
            not isinstance(self.traceback_policy, TracebackOptions)
            and self.traceback_policy is not None
        ):
            raise ValueError("traceback_policy must be a TracebackOptions enum value")

        if (
            not isinstance(self.path_resolution, PathResolutionSetting)
            and self.path_resolution is not None
        ):
            raise ValueError("path_resolution must be a PathResolutionSetting enum value")
