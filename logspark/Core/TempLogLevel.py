from collections.abc import Callable
from functools import wraps
from types import TracebackType
from typing import TYPE_CHECKING, Any

from .._Internal.Func import validate_level

if TYPE_CHECKING:
    from .SparkLogger import SparkLogger


class TempLogLevel:
    """
    Context manager and decorator for temporary logging level adjustments.

    Temporarily changes the SparkLogger's effective level without touching
    the frozen configuration. The original level is restored automatically
    when the scope exits or the decorated function returns.

    Usage as a context manager::

        with TempLogLevel(logging.DEBUG):
            logger.debug("visible only inside this block")

    Usage as a decorator::

        @TempLogLevel(logging.DEBUG)
        def process_order(order_id: str) -> None:
            logger.debug("visible during this call")

    Only the logger level is affected. Handlers, formatters, filters, and
    the frozen configuration remain unchanged.
    """

    def __init__(self, level: str | int) -> None:
        """Store and validate the target level."""
        v_level = validate_level(level)

        self.target_level = v_level
        self.original_level: int | None = None
        self.logger_instance: "SparkLogger | None" = None

    def __enter__(self) -> "TempLogLevel":
        """Enter the override context - adjust logger's effective level"""
        # Get the global logger singleton
        from .SparkLogger import SparkLogger

        self.logger_instance = SparkLogger()

        # Store original level for restoration
        self.original_level = self.logger_instance.level

        # Apply temporary level override
        # This only affects the stdlib logger's effective level, not the configuration
        self.logger_instance.setLevel(self.target_level)
        # SparkLogger is removed from loggerDict by kill(), so manager._clear_cache()
        # (called inside setLevel) never reaches it. Clear the isEnabledFor cache
        # explicitly so the new level is picked up immediately.
        self.logger_instance._cache.clear()  # type: ignore[attr-defined]

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
            self.logger_instance.setLevel(self.original_level)
            self.logger_instance._cache.clear()  # type: ignore[attr-defined]

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
