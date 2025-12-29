import logging
import threading
from typing import Optional, TYPE_CHECKING

from .Types import UnfrozenGlobalOperationError
from .Types import InvalidConfigurationError
from .Internal.State import SingletonClass
from .Internal.State import LogManagerState

if TYPE_CHECKING:
    from . import SparkLogger


@SingletonClass
class SparkLogManager:
    """
    LogManager singleton for explicit global logging management.

    Provides opt-in global control over multiple loggers while maintaining
    stdlib compliance. Allows you to adopt existing loggers and apply
    consistent formatting across your entire application.

    The LogManager operates on a "managed logger" concept where you explicitly
    choose which loggers to control, rather than automatically affecting all
    logging in the application.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._state = LogManagerState(managed_loggers={})

        # Passively manage only LogSpark's logger by default
        self._state.managed_loggers["LogSpark"] = logging.getLogger("LogSpark")

    def adopt_all(self) -> None:
        """
        Adopt all loggers currently present in the logging registry.

        This method scans the standard library's logging registry and adds
        all existing Logger instances to the managed logger collection.
        Only actual Logger instances are adopted (not PlaceHolder objects).

        Note:
            This is a snapshot operation - loggers created after calling
            adopt_all() will not be automatically managed. Call this method
            again if you need to adopt newly created loggers.

        Example:
            ```python
            from logspark import LogManager

            # Adopt all existing loggers
            LogManager.adopt_all()

            # Now you can access any logger by name
            django_logger = LogManager.managed("django")
            ```
        """
        with self._lock:
            # Get current loggers from logging registry
            current_loggers = logging.Logger.manager.loggerDict.copy()

            for name, logger_obj in current_loggers.items():
                if isinstance(logger_obj, logging.Logger):
                    self._state.managed_loggers[name] = logger_obj

    def managed(self, name: str) -> logging.Logger:
        """
        Return a managed logger by name.

        Args:
            name: The name of the logger to retrieve. This should match
                 the name used when the logger was created or adopted.

        Returns:
            The standard library logging.Logger instance for the given name.

        Raises:
            KeyError: If the specified logger name is not currently managed.
                     Call adopt_all() first to adopt existing loggers, or ensure
                     the logger was created after adoption.

        Example:
            ```python
            from logspark import LogManager

            LogManager.adopt_all()

            # Get a specific managed logger
            app_logger = LogManager.managed("myapp")
            app_logger.info("This uses the managed logger")
            ```
        """
        with self._lock:
            if name not in self._state.managed_loggers:
                raise KeyError(f"Logger '{name}' is not managed. Call adopt_all() first.")
            return self._state.managed_loggers[name]

    def unify_format(self, logger_instance: Optional["SparkLogger"] = None) -> None:
        """
        Apply LogSpark's handler and formatter configuration to all managed loggers.

        This method takes the configuration from a LogSpark logger and applies
        the same handler and logging level to all managed loggers, creating
        consistent formatting across your entire application.

        Args:
            logger_instance: The LogSpark logger instance to copy configuration from.
                           If None, uses the global LogSpark logger singleton.

        Raises:
            InvalidConfigurationError: If the source logger hasn't been configured yet.

        Note:
            The source logger must be configured before calling this method.
            All managed loggers will have their existing handlers cleared and
            replaced with the LogSpark configuration.

        Example:
            ```python
            from logspark import logger, LogManager
            from logspark.handlers import JSONHandler

            # Configure LogSpark logger
            logger.configure(
                level=logging.INFO,
                format=JSONHandler()
            )

            # Adopt existing loggers and unify their format
            LogManager.adopt_all()
            LogManager.unify_format()

            # Now all managed loggers use JSON formatting
            ```
        """
        if logger_instance is None:
            from .SparkLoggerDef import spark_logger

            logger_instance = spark_logger

        with self._lock:
            # Get LogSpark logger configuration
            if not logger_instance.is_frozen:
                if logger_instance._config is None:
                    raise InvalidConfigurationError("LogSpark logger not configured")
                else:
                    raise UnfrozenGlobalOperationError(
                        "LogSpark logger needs to be frozen before calling this method"
                    )

            # Apply configuration to all managed loggers
            for managed_logger in self._state.managed_loggers.values():
                if managed_logger != logger_instance.instance:
                    # Clear existing handlers
                    managed_logger.handlers.clear()
                    # Apply LogSpark's handler and level
                    managed_logger.setLevel(logger_instance.config.level)
                    managed_logger.addHandler(logger_instance.config.handler)

    def release(self) -> None:
        """
        Release all managed loggers and reset the LogManager state.

        This method relinquishes ownership of all managed loggers and clears
        internal state. After calling release(), the LogManager behaves as if
        freshly imported and manages no loggers until explicitly instructed
        to do so again.

        This operation does NOT attempt to restore previous handler or formatter
        configurations on managed loggers. Any global formatting changes applied
        via unify_format() remain in effect.

        Intended for controlled teardown, test isolation, or explicit lifecycle
        management.
        """
        with self._lock:
            # Drop all managed loggers
            self._state.managed_loggers.clear()

            # Reset internal state to a clean baseline with default LogSpark management
            self._state = LogManagerState(managed_loggers={})
            # Passively manage only LogSpark's logger by default (same as __init__)
            self._state.managed_loggers["LogSpark"] = logging.getLogger("LogSpark")

            # Reset singleton slot so a fresh instance can be created
            cls = self.__class__
            if hasattr(cls, "_SingletonWrapper__cls_instance"):
                setattr(cls, "_SingletonWrapper__cls_instance", None)


spark_log_manager = SparkLogManager()
