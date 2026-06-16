import logging
import threading
from typing import TYPE_CHECKING, Callable

from .._Internal.Func import validate_level
from .._Internal.State import LogManagerState
from ..Types import InvalidConfigurationError, UnfrozenGlobalOperationError
from ..Types.Protocol import SupportsFilter

if TYPE_CHECKING:
    from . import SparkLogger


class SparkLogManager:
    """
    Utility for explicit, opt-in batch mutation of stdlib loggers.

    Provides a controlled way to apply standard logging operations (handler
    replacement, level changes, propagation control) across a selected set of
    existing ``logging.Logger`` instances.

    This class does NOT:
    - replace loggers
    - wrap or proxy logging calls
    - modify the logging registry
    - intercept log record dispatch
    - restore previous logger state

    Adoption is explicit and snapshot-based: only loggers that exist at the
    time of ``adopt_all()`` are affected. Loggers created afterwards are not
    managed unless explicitly adopted via ``adopt()``.

    ``release_all()`` returns the manager to an empty state matching
    construction. It does not undo mutations applied via ``unify()``.
    """

    def __init__(self) -> None:
        """Initialize a new manager with an empty managed-logger set."""
        self._lock = threading.RLock()
        self._state = LogManagerState(managed_loggers={})

    # -----Management-----
    @property
    def managed_names(self) -> list[str]:
        """
        Return the names of all currently managed loggers.

        This reflects the current contents of the manager's internal snapshot.
        The returned list is sorted and contains logger names only.

        This property is informational and does not imply ownership or control
        beyond explicit mutation methods such as ``unify`` or ``release``.
        """
        managed_loggers = []
        for logger in self._state.managed_loggers.values():
            managed_loggers.append(logger.name)
        managed_loggers.sort()
        return managed_loggers

    def managed(self, name: str) -> logging.Logger:
        """
        Retrieve a managed logger by name.

        Raises ``KeyError`` if the name is not in the current managed set.
        Returns the actual ``logging.Logger`` object; further direct mutations
        by the caller are not restricted.
        """
        with self._lock:
            if name not in self._state.managed_loggers:
                raise KeyError(
                    f"Logger '{name}' is not managed. Call adopt_all() or check managed loggers first."
                )
            return self._state.managed_loggers[name]

    # -----Adoption-----
    def adopt(self, logger: logging.Logger) -> None:
        """
        Add a single logger to the managed set.

        No mutation occurs at adoption time. The logger remains independently
        accessible and mutable by other code.
        """
        with self._lock:
            self._state.managed_loggers[logger.name] = logger

    def adopt_all(self, ignore: list[str] | None = None, ignore_spark: bool = True) -> None:
        """
        Snapshot the logging registry and adopt all concrete loggers found.

        This is a point-in-time operation. Loggers created after this call are
        not managed unless explicitly adopted via ``adopt()``. ``PlaceHolder``
        entries in the registry are ignored. By default the ``"LogSpark"``
        logger is excluded via ``ignore_spark=True``.
        """
        ignore = list(ignore) if ignore is not None else []

        if ignore_spark:
            ignore.append("LogSpark")

        with self._lock:
            # Get current loggers from logging registry
            current_loggers = logging.Logger.manager.loggerDict.copy()

            for name, logger_obj in current_loggers.items():
                if isinstance(logger_obj, logging.Logger):
                    if name not in ignore:
                        self._state.managed_loggers[name] = logger_obj

    # ----- Release -----
    def release(self, name: str) -> None:
        """
        Remove a single logger from the managed set.

        No mutation or restoration of logger state is performed.
        Raises ``KeyError`` if the name is not currently managed.
        """
        with self._lock:
            if name not in self._state.managed_loggers:
                raise KeyError(
                    f"Logger '{name}' is not managed. Call adopt_all() or check managed loggers first."
                )
            self._state.managed_loggers.pop(name)

    def release_all(self) -> None:
        """
        Release all managed loggers and reset manager state.

        This clears the internal managed snapshot and resets the manager to
        an empty baseline. No attempt is made to restore previous handler,
        level, or propagation state on any logger.

        This method is intended for:
        - test isolation
        - controlled teardown
        - explicit lifecycle management

        It does not undo mutations applied via ``unify``.
        """

        with self._lock:
            self._state = LogManagerState(managed_loggers={})

    # -----Mutators-----
    def unify(
        self,
        /,
        level: int | str | None = None,
        handlers: list[logging.Handler] | None = None,
        filters: list[logging.Filter | Callable[[logging.LogRecord], bool] | SupportsFilter]
        | None = None,
        propagate: bool | None = None,
        spark_logger_instance: "SparkLogger | None" = None,
    ) -> None:
        """
        Apply logging mutations to all managed loggers in a single batch call.

        All parameters are optional. Only the ones supplied are applied:

        - ``level`` — set the effective log level on each managed logger.
        - ``handlers`` — replace existing handlers; the same list is shared
          across all managed loggers. Existing handlers are cleared first.
        - ``filters`` — replace existing filters similarly.
        - ``propagate`` — override the ``propagate`` flag on each managed logger.
        - ``spark_logger_instance`` — copy handlers and filters from the
          supplied ``SparkLogger`` instance instead of specifying them explicitly.
          Pass ``None`` (the default) to skip config copying. Requires the
          supplied instance to be configured and frozen; raises
          ``InvalidConfigurationError`` or ``UnfrozenGlobalOperationError``
          otherwise.

        This operation is destructive and deliberately does not track previous
        state. ``release()`` / ``release_all()`` do not undo applied mutations.
        """
        with self._lock:
            # Get LogSpark logger configuration
            if spark_logger_instance is not None:
                from . import SparkLogger

                if not isinstance(spark_logger_instance, SparkLogger):
                    raise TypeError("spark_logger_instance must be an instance of SparkLogger")

                if not spark_logger_instance.frozen:
                    if not spark_logger_instance.is_configured:
                        raise InvalidConfigurationError("LogSpark logger not is_configured")
                    else:
                        raise UnfrozenGlobalOperationError(
                            "LogSpark logger needs to be frozen before copying its handlers"
                        )
                if not handlers:
                    # noinspection PyTypeChecker,PydanticTypeChecker
                    handlers = list(spark_logger_instance.handlers)
                if not filters:
                    # noinspection PyTypeChecker,PydanticTypeChecker
                    filters = list(spark_logger_instance.filters)

            if level is not None:
                v_level = validate_level(level)
            else:
                v_level = None

            # Apply configuration to all managed loggers
            for managed_logger in self._state.managed_loggers.values():
                # Clear existing handlers
                if handlers:
                    managed_logger.handlers.clear()

                    for h in handlers:
                        managed_logger.addHandler(h)
                if filters:
                    managed_logger.filters.clear()
                    for f in filters:
                        managed_logger.addFilter(f)
                if v_level is not None:
                    managed_logger.setLevel(v_level)
                if propagate is not None:
                    managed_logger.propagate = propagate
