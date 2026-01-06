from collections.abc import Callable
from functools import wraps
from types import TracebackType
from typing import TYPE_CHECKING, Any

from ._Internal.Func import validate_level

if TYPE_CHECKING:
    from . import SparkLogger


class LogOverride:
    """
    Context manager and decorator for temporary logging level adjustments.

    Provides scoped debugging capabilities by temporarily changing the logger's
    effective level without modifying the frozen configuration. The original
    level is automatically restored when the scope ends.

    This is useful for debugging specific code sections or functions without
    permanently changing your logger configuration.

    Usage as context manager:
        ```python
        from logspark import logger, LogOverride
        import logging

        logger.configure(level=logging.INFO)

        with LogOverride(level=logging.DEBUG):
            logger.debug("This debug message is now visible")
        # Debug level is automatically restored to INFO
        ```

    Usage as decorator:
        ```python
        @LogOverride(level=logging.DEBUG)
        def debug_function():
            logger.debug("This debug message is now visible")
            # Function runs with DEBUG level enabled
        ```

    Note:
        LogOverride only affects the effective logging level, not handlers,
        formatters, or other configuration aspects. The frozen configuration
        remains immutable.
    """

    def __init__(self, level: str | int):
        """
        Initialize LogOverride with the target logging level.

        Args:
            level: Target logging level for the override scope. Should be one of
                  the standard library logging levels (e.g., logging.DEBUG,
                  logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL).

        Raises:
            InvalidConfigurationError: If level is not a valid integer.

        Example:
            ```python
            # Create override for DEBUG level
            debug_override = LogOverride(logging.DEBUG)
            ```
        """
        v_level = validate_level(level)

        self.target_level = v_level
        self.original_level: int | None = None
        self.logger_instance: "SparkLogger | None" = None

    def __enter__(self) -> "LogOverride":
        """Enter the override context - adjust logger's effective level"""
        # Get the global logger singleton
        from . import SparkLogger

        self.logger_instance = SparkLogger()

        # Store original level for restoration
        self.original_level = self.logger_instance.instance.level

        # Apply temporary level override
        # This only affects the stdlib logger's effective level, not the configuration
        self.logger_instance.instance.setLevel(self.target_level)

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the override context - restore original level"""
        if self.logger_instance is not None and self.original_level is not None:
            # Restore original level
            self.logger_instance.instance.setLevel(self.original_level)

        # Clear references
        self.logger_instance = None
        self.original_level = None

    def __call__(self, func: Callable[[Any, Any], Any]) -> Any:
        """
        Decorator usage - wrap function with LogOverride context

        Args:
            func: Function to wrap with logging override

        Returns:
            Wrapped function that applies LogOverride during execution
        """

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self:
                return func(*args, **kwargs)

        return wrapper
