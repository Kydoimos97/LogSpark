import logging
import threading
from typing import TYPE_CHECKING

from ._Internal.Func import validate_level
from ._Internal.State import LogManagerState, SingletonClass
from .Types import InvalidConfigurationError, UnfrozenGlobalOperationError

if TYPE_CHECKING:
    pass


@SingletonClass
class SparkLogManager:
    """
    Global SparkLogManager singleton instance.

    This instance provides a shared coordination point for logger adoption and
    batch mutation within a process. Use is entirely opt-in.
    """

    def __init__(self) -> None:
        """
        Singleton utility for explicit, opt-in batch mutation of stdlib loggers.

        SparkLogManager provides a controlled way to apply standard logging
        operations (handler replacement, level changes, propagation control)
        across a selected set of existing ``logging.Logger`` instances.

        This class does NOT:
        - replace loggers
        - wrap or proxy logging calls
        - modify the logging registry
        - intercept log record dispatch
        - restore previous logger state

        It does not have ownership or hierarchy over
        managed loggers. It operates strictly by mutating
        already-created Logger objects using normal stdlib mechanisms.

        Adoption is explicit and snapshot-based: only loggers that exist at the
        time of adoption are affected. Loggers created later are not managed
        unless explicitly adopted at a later time.

        The singleton exists to provide a single coordination point for applying
        logging policy in a process
        """
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

        Args:
            name: Name of the logger as returned by ``logging.Logger.name``.

        Returns:
            The managed stdlib Logger instance.

        Raises:
            KeyError: If the logger is not currently managed.

        This method provides access to the actual Logger object and does not
        restrict or mediate further direct mutations performed by the caller.
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
        Adopt a single existing ``logging.Logger`` instance.

        Adoption stores a reference to the logger and makes it eligible for
        subsequent batch operations. No mutation occurs at adoption time.

        Args:
            logger: An existing stdlib Logger instance to manage.

        Note:
            Adoption does not modify the logger and does not prevent other
            code from mutating it independently.
        """
        with self._lock:
            self._state.managed_loggers[logger.name] = logger

    def adopt_all(self, ignore: list[str] | None = None, ignore_spark: bool = True) -> None:
        """
        Adopt all existing stdlib loggers currently registered.

        This method snapshots the logging registry and adopts all concrete
        ``logging.Logger`` instances present at the time of the call.

        Args:
            ignore: Optional list of logger names to exclude from adoption.
            ignore_spark: When True, excludes the ``"LogSpark"`` logger by default.

        Notes:
            - This is a snapshot operation. Loggers created after this call
              are not managed unless explicitly adopted later.
            - PlaceHolder entries in the logging registry are ignored.
            - Adoption does not mutate any logger state.

        This method intentionally performs no forward-looking tracking and
        does not re-check the registry automatically.
        """
        if ignore is None:
            ignore = []

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
        Stop managing a specific logger.

        This removes the logger from the managed snapshot. No mutation or
        restoration of logger state is performed.

        Args:
            name: Name of the managed logger to release.

        Raises:
            KeyError: If the logger is not currently managed.
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
            # Drop all managed loggers
            self._state.managed_loggers.clear()

            # Reset internal state to a clean baseline with default LogSpark management
            self._state = LogManagerState(managed_loggers={})
            # Passively manage only LogSpark's logger by default (same as __init__)
            self._state.managed_loggers["LogSpark"] = logging.getLogger("LogSpark")

            # Reset singleton slot so a fresh instance can be created
            cls = self.__class__
            if hasattr(cls, "_SingletonWrapper__cls_instance"):
                cls._SingletonWrapper__cls_instance = None

    # -----Mutators-----
    def unify(
        self,
        /,
        level: int | str | None = None,
        handler: logging.Handler | None = None,
        propagate: bool | None = None,
        use_spark_handler: bool = False,
    ) -> None:
        """
        Apply standard logging mutations to all managed loggers.

        This method performs batch mutation of managed Logger instances using
        normal stdlib operations. It may replace handlers, adjust log levels,
        and modify propagation behavior.

        Args:
            level:
                Logging level to apply to each managed logger. When None,
                the logger's existing level is preserved.

            handler:
                Handler instance to attach to each managed logger. When provided,
                existing handlers are cleared and the given handler is attached.

                The same handler instance is shared across all managed loggers.

            propagate:
                Value to assign to ``logger.propagate`` for each managed logger.
                When None, propagation behavior is left unchanged.

            use_spark_handler:
                When True and ``handler`` is None, copies the handler from the
                frozen LogSpark logger. This requires LogSpark to be configured
                and frozen.

        Raises:
            InvalidConfigurationError:
                If ``use_spark_handler`` is True but LogSpark is not configured.

            UnfrozenGlobalOperationError:
                If LogSpark exists but is not frozen when attempting to copy
                its handler.

            ValueError:
                If ``handler`` is provided and is not a logging.Handler.

        Important:
            - This operation is destructive: existing handlers are removed.
            - Previous logger state is not preserved or restored.
            - Release does not revert applied mutations.

        This method applies policy once and deliberately avoids reconciliation
        or state tracking beyond the managed snapshot.
        """
        with self._lock:
            # Get LogSpark logger configuration
            if handler is None:
                if use_spark_handler:
                    from .SparkLoggerDef import spark_logger

                    if not spark_logger.is_frozen:
                        if spark_logger._config is None:
                            raise InvalidConfigurationError("LogSpark logger not frozen")
                        else:
                            raise UnfrozenGlobalOperationError(
                                "LogSpark logger needs to be frozen before copying its handler"
                            )
                    # You cannot freeze without a config
                    assert spark_logger._config is not None
                    handler = spark_logger._config.handler
            elif not isinstance(handler, logging.Handler):
                raise ValueError("Handler must be a logging.Handler instance")

            if level is not None:
                v_level = validate_level(level)
            else:
                v_level = None

            # Apply configuration to all managed loggers
            for managed_logger in self._state.managed_loggers.values():
                # Clear existing handlers
                if handler is not None:
                    managed_logger.handlers.clear()
                    managed_logger.addHandler(handler)
                if v_level is not None:
                    managed_logger.setLevel(v_level)
                if propagate is not None:
                    managed_logger.propagate = propagate


# Singleton Pattern
spark_log_manager = SparkLogManager()
