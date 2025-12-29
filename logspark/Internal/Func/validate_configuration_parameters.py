import logging
from typing import Optional

from ...Types import InvalidConfigurationError
from ...Types import TracebackOptions


def validate_configuration_parameters(
    level: int, fast_log: bool, handler: Optional[logging.Handler], traceback: TracebackOptions
) -> None:
    """
    Validate configuration parameters

    Args:
        level: Logging level to validate
        fast_log: Fast log flag to validate
        handler: Handlers to validate
        traceback: Traceback policy to validate

    Raises:
        InvalidConfigurationError: If any parameter is invalid
    """
    # Validate level is a valid integer (stdlib logging accepts any integer)
    if not isinstance(level, int):
        raise InvalidConfigurationError(f"level must be an integer, got {type(level)}")

    # Validate fast_log is boolean
    if not isinstance(fast_log, bool):
        raise InvalidConfigurationError(f"fast_log must be a boolean, got {type(fast_log)}")

    # Validate format is a Handlers instance (can be None for default)
    if handler is not None and not isinstance(handler, logging.Handler):
        raise InvalidConfigurationError(
            f"handler must be a logging.Handlers instance, got {type(handler)}"
        )

    # Validate traceback policy
    if not isinstance(traceback, TracebackOptions):
        raise InvalidConfigurationError(
            f"traceback must be a TracebackOptions enum value, got {type(traceback)}"
        )
