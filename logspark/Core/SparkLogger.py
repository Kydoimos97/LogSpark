import logging
import threading
from typing import Any

from .._Internal.Func import emit_warning, resolve_stacklevel, validate_level
from .._Internal.State import SingletonClass, is_fast_mode
from .._Internal.State.Env import is_ddtrace_available
from ..Filters import PathNormalizationFilter
from ..Filters.DDTraceInjectionFilter import DDTraceInjectionFilter
from ..Filters.TracebackPolicyFilter import TracebackPolicyFilter
from ..Handlers import SparkPreConfigHandler, SparkTerminalHandler
from ..Types import (
    FrozenClassException,
    InvalidConfigurationError,
    SparkLoggerDuplicatedFilterWarning,
    SparkLoggerDuplicatedHandlerWarning,
    SparkLoggerUnconfiguredUsageWarning,
)
from ..Types.Options import PathResolutionSetting, TracebackOptions


@SingletonClass
class SparkLogger(logging.Logger):
    """
    Singleton logger with explicit configuration and freeze semantics.

    Lifecycle: ``configure()`` → (optional) ``freeze()`` → use → (optional) ``kill()``.
    Once frozen, all handler, filter, and level configuration is immutable for the
    lifetime of the instance. ``kill()`` tears down the singleton and clears the
    stdlib logger registry entry, allowing a fresh ``configure()`` call.

    Pre-configuration usage is allowed: a one-time warning is emitted and
    ``SparkPreConfigHandler`` is attached as a fallback so no records are silently
    dropped. Calling ``configure()`` replaces that fallback with the real handler.

    All standard ``logging.Logger`` methods (``debug``, ``info``, ``warning``,
    ``error``, ``critical``, ``exception``, ``log``) are available directly on
    this instance. ``extra=`` kwargs are forwarded unchanged for structured fields.
    """

    def __init__(self) -> None:
        super().__init__("LogSpark")
        self._lock = threading.RLock()
        self._stdlib_logger: logging.Logger | None = None
        self._logger_name = "LogSpark"

        self._configured = False
        self._frozen = False
        self._pre_config_setup_done = False
        self._unconfigured_warning_emitted = False

        self._ensure_pre_config_setup()

    # PUBLIC LOGGING API
    def debug(self, msg: object, *args: object, **kwargs: Any) -> None:
        """Log a message at DEBUG level."""
        self._ensure_config()
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: object, *args: object, **kwargs: Any) -> None:
        """Log a message at INFO level."""
        self._ensure_config()
        self._log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: object, *args: object, **kwargs: Any) -> None:
        """Log a message at WARNING level."""
        self._ensure_config()
        self._log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: object, *args: object, **kwargs: Any) -> None:
        """Log a message at ERROR level."""
        self._ensure_config()
        self._log(logging.ERROR, msg, *args, **kwargs)

    def critical(self, msg: object, *args: object, **kwargs: Any) -> None:
        """Log a message at CRITICAL level."""
        self._ensure_config()
        self._log(logging.CRITICAL, msg, *args, **kwargs)

    def exception(self, msg: object, *args: object, **kwargs: Any) -> None:
        """
        Log a message at ERROR level and attach current exception information.

        Must be called from within an ``except`` block. ``exc_info=True`` is
        set automatically; the traceback policy on the record governs how
        the exception is rendered.
        """
        self._ensure_config()
        kwargs.setdefault("exc_info", True)
        self._log(logging.ERROR, msg, *args, **kwargs)

    def log(self, level: int, msg: object, *args: object, **kwargs: Any) -> None:
        """
        Log a message at an explicit numeric severity level.

        Mirrors the stdlib ``Logger.log()`` entry point for compatibility with
        generic logging utilities. All LogSpark invariants are preserved:
        configuration and freeze semantics, deterministic callsite resolution,
        and handler/traceback policy enforcement.
        """
        self._ensure_config()
        self._log(level, msg, *args, **kwargs)

    # PUBLIC SETTINGS API -- LifeCycle
    def configure(
        self,
        level: str | int = logging.INFO,
        *,
        handler: logging.Handler | None = None,
        traceback_policy: TracebackOptions | None = TracebackOptions.COMPACT,
        path_resolution: PathResolutionSetting | None = PathResolutionSetting.RELATIVE,
        multiline: bool = True,
        no_freeze: bool = False,
    ) -> None:
        """
        Configure the logger and, by default, freeze it immediately.

        This is the primary entry point for LogSpark setup. It must be called
        before the logger is used in production. Calling it a second time on a
        frozen instance raises ``FrozenClassException``.

        When no handler is supplied, a ``SparkTerminalHandler`` is created with
        the given ``traceback_policy`` and ``multiline`` settings. If
        ``LOGSPARK_MODE=fast`` is set in the environment, a ``NullHandler`` is
        used instead for maximum throughput.

        The ``no_freeze=True`` flag is intended for advanced use cases (e.g.
        adding extra handlers or filters after initial configuration). Call
        ``logger.freeze()`` manually when setup is complete.
        """
        with self._lock:
            if self._frozen:
                raise FrozenClassException("Cannot configure logger after freeze")

            log_level = validate_level(level)

            # Default to SparkTerminalHandler if none provided
            if is_fast_mode() and handler is None:
                # Fast logging with no explicit handler - use NullHandler for maximum speed
                hdl: logging.Handler = logging.NullHandler()
            elif handler is None:
                hdl = SparkTerminalHandler(level=log_level, traceback_policy=traceback_policy, multiline=multiline)
            else:
                hdl = handler

            # ensure we have a name
            hdl.name = getattr(hdl, "name", self._logger_name)

            self._apply_config(log_level, handler=hdl, traceback_policy=traceback_policy, path_resolution=path_resolution, multiline=multiline)

            # no freeze for power user
            if not no_freeze:
                self._frozen = True


    def _apply_config(self, level: str | int = logging.INFO, *, handler: logging.Handler,
        traceback_policy: TracebackOptions | None = None, path_resolution: PathResolutionSetting | None = None, multiline: bool = True):
        """Apply filters, handler, level, and ddtrace injection to the logger."""
        if traceback_policy is not None:
            self.addFilter(
                    TracebackPolicyFilter()
            )

        if path_resolution is not None:
            self.addFilter(PathNormalizationFilter(resolution_mode=path_resolution))

        # Clear existing handlers but preserve filters (including ddtrace)
        self.eject_handlers()

        self.setLevel(level)
        self.addHandler(handler)

        # Ensure ddtrace filter is present (idempotent)
        if is_ddtrace_available() and not any(
            isinstance(f, DDTraceInjectionFilter) for f in self.filters
        ):
            log_filter = DDTraceInjectionFilter()
            self.addFilter(log_filter)

        self.is_configured = True

    @property
    def is_configured(self) -> bool:
        """True after a successful ``configure()`` call."""
        return self._configured

    @is_configured.setter
    def is_configured(self, value: bool):
        """Set the configured flag; raises ``InvalidConfigurationError`` if set True with no handlers."""
        if value is True:
            if not self.handlers:
                raise InvalidConfigurationError("No handlers provided in current configuration set a handler with logger.addHandler()")
        self._configured = value

    def eject_handlers(self) -> None:
        """
        Flush, close, and remove all attached handlers.

        Raises ``FrozenClassException`` if the logger is frozen. Intended for
        reconfiguration flows (e.g. replacing the handler between ``configure``
        calls when ``no_freeze=True``). Not part of the normal production
        lifecycle.
        """
        if self.frozen:
            raise FrozenClassException("Cannot eject handlers from frozen logger")

        for _handler in self.handlers:
            _handler.flush()
            _handler.close()
        self.handlers.clear()

    def eject_filters(self) -> None:
        """
        Remove all attached filters.

        Raises ``FrozenClassException`` if the logger is frozen.
        """
        if self.frozen:
            raise FrozenClassException("Cannot eject filters from frozen logger")
        self.filters.clear()

    def addHandler(self, hdlr, dedupe: bool = False):
        """
        Attach a handler, enforcing freeze semantics and optional deduplication.

        Raises ``FrozenClassException`` if the logger is frozen. If a handler of
        the same type is already attached, emits ``SparkLoggerDuplicatedHandlerWarning``
        unless ``dedupe=True``, in which case the existing handler is removed first.
        """
        if self.frozen:
            raise FrozenClassException("Cannot add handlers to frozen logger")
        with self._lock:
            for h in self.handlers:
                if isinstance(hdlr, type(h)):
                    if dedupe:
                        self.handlers.remove(h)
                    else:
                        emit_warning(
                            message="\nWARNING: Duplicate active handler classes: {name}\n"
                            "  | This warning indicates that a addHandler call would create a duplicate logging.Handler;\n"
                            "  | If this is not intended, consider using dedupe=True to avoid duplicates.".format(name=type(hdlr).__name__),
                            category=SparkLoggerDuplicatedHandlerWarning,
                            stacklevel=4,
                        )
            super().addHandler(hdlr)

    def addFilter(self, filter, dedupe: bool = False):
        """
        Attach a filter, enforcing freeze semantics and optional deduplication.

        Raises ``FrozenClassException`` if the logger is frozen. If a filter of
        the same type is already attached, emits ``SparkLoggerDuplicatedFilterWarning``
        unless ``dedupe=True``, in which case the existing filter is removed first.
        """
        if self.frozen:
            raise FrozenClassException("Cannot add filters to frozen logger")
        with self._lock:
            for f in self.filters:
                if isinstance(filter, type(f)):
                    if dedupe:
                        self.filters.remove(f)
                    else:
                        emit_warning(
                            message="\nWARNING: Duplicate active filter classes: {name}\n"
                            "  | This warning indicates that a addFilter call would create a duplicate logging.Filter;\n"
                            "  | If this is not intended, consider using dedupe=True to avoid duplicates.".format(name=type(filter).__name__),
                            category=SparkLoggerDuplicatedFilterWarning,
                            stacklevel=4,
                        )
            super().addFilter(filter)

    def freeze(self) -> None:
        """
        Make the logger configuration immutable.

        Called automatically by ``configure()`` unless ``no_freeze=True`` was
        passed. After freezing, ``addHandler()``, ``addFilter()``,
        ``eject_handlers()``, and ``eject_filters()`` all raise
        ``FrozenClassException``.

        Raises ``InvalidConfigurationError`` if called before ``configure()``.
        Idempotent — calling it on an already-frozen logger is a no-op.
        """
        if self._frozen:
            return

        if self._configured is not True:
            raise InvalidConfigurationError(
                "The logger has to be is_configured by calling configure(...) or setting is_configured before you can freeze it."
            )

        self._frozen = True

    @property
    def frozen(self) -> bool:
        """True once the logger has been configured and frozen."""
        return self._frozen

    @frozen.setter
    def frozen(self, value: bool):
        """Assign True to freeze; assigning False raises ``ValueError``."""
        if value is True:
            self.freeze()
        else:
            raise ValueError("Cannot unfreeze a logger once it has been frozen to create a new instance call kill()")

    def kill(self) -> None:
        """
        Forcefully tear down the logger and reset the singleton.

        This method bypasses the normal LogSpark lifecycle guarantees
        (configure → freeze → use). It exists to support test isolation,
        controlled reinitialization, and advanced tooling.

        After calling this method:
          - the current instance is fully deconfigured
          - the singleton slot is cleared
          - the next SparkLogger() call creates a new instance

        WARNING:
            This is not part of the intended production lifecycle.
            Calling this in a live application may lead to inconsistent
            logging behavior if other components retain references to
            the old stdlib logger.
        """
        with self._lock:
            # Tear down stdlib logger
            name = self.name
            self._frozen = False
            for h in self.handlers[:]:
                self.removeHandler(h)
                h.close()

            self.eject_filters()

            logging.Logger.manager.loggerDict.pop(name, None)

            # Removing from loggerDict prevents manager._clear_cache() from reaching
            # this logger, so stale isEnabledFor cache entries must be cleared explicitly.
            getattr(self, "_cache", {}).clear()

            # Reset instance state
            self._configured = False
            self._frozen = False
            self._pre_config_setup_done = False
            self._unconfigured_warning_emitted = False

            # Intentionally do not reset Singleton slot
            # this maintains the relationship between singleton and
            # the global logging registry

    def _log(self, level: int, msg: object, *args: object, **kwargs: Any) -> None:
        """Resolve stacklevel and delegate to stdlib ``Logger._log``."""
        if not isinstance(level, int):
            if logging.raiseExceptions:
                raise TypeError("level must be an integer")
            else:
                return

        if not self.isEnabledFor(level):
            return

        user_stacklevel = kwargs.get("stacklevel", 1)

        # Resolve appropriate stacklevel to point to actual calling code
        resolved_stacklevel = resolve_stacklevel(user_stacklevel)
        kwargs["stacklevel"] = resolved_stacklevel
        super()._log(level, msg, args, **kwargs)

    def _ensure_config(self) -> None:
        """Emit unconfigured warning and attach pre-config handler if configure() has not been called."""
        if self._configured is not True and not self._pre_config_setup_done:
            self._emit_unconfigured_warning()
            self._ensure_pre_config_setup()

    def _ensure_pre_config_setup(self) -> None:
        """Attach SparkPreConfigHandler as a one-time fallback before configure() is called."""
        if self._pre_config_setup_done:
            return

        with self._lock:
            # Create stdlib logger with LogSpark defaults
            if self.handlers:
                self._raise_logger_name_conflict()
                return

            self.setLevel(logging.INFO)
            # Detect stdlib handler as fallback
            handler = SparkPreConfigHandler()
            self.addHandler(handler)

            self._pre_config_setup_done = True

    def _emit_unconfigured_warning(self) -> None:
        """Emit a one-time SparkLoggerUnconfiguredUsageWarning."""
        if not self._unconfigured_warning_emitted:
            emit_warning(
                message="\nWARNING: Logger used before configuration.\n"
                "  | This warning indicates a lifecycle violation;\n"
                "  | call logger.configure() before logging",
                category=SparkLoggerUnconfiguredUsageWarning,
                stacklevel=4,
            )
            self._unconfigured_warning_emitted = True

    def _raise_logger_name_conflict(self) -> None:
        """Raise RuntimeError when a conflicting logger name already exists in the registry."""
        raise RuntimeError(
            (
                "\nLogSpark invariant violation detected.\n"
                "  | A logger named '{name}' already exists in the global logging registry.\n"
                "  | LogSpark's Singleton Instance requires exclusive ownership of its managed logger,\n"
                "  | to guarantee single-configuration, determinism, and auditability.\n"
                "  |\n"
                "  | This indicates a race condition, re-entrant initialization,\n"
                "  | or external mutation of logging state prior to LogSpark configuration.\n"
                "  |\n"
                "  | LogSpark cannot safely continue in this state and uphold its invariants.\n"
                "  | Ensure logging is is_configured exactly once, early in process startup,\n"
                "  | before any threads, workers, or process pools are created.\n"
                "  | No other code may create or configure this logger name.\n"
            ).format(name=self._logger_name)
        )
