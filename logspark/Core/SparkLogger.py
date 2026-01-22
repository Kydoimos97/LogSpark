import logging
import threading
from typing import Any

from .._Internal.Func import emit_warning, resolve_stacklevel, validate_level
from .._Internal.State import LoggerConfig, SingletonClass, is_fast_mode
from .._Internal.State.Env import is_ddtrace_available
from ..Filters import PathNormalization, TracebackPolicy
from ..Filters.DDTraceInjection import DDTraceInjection
from ..Handlers import PreConfigHandler
from ..Types import (
    FrozenConfigurationError,
    InvalidConfigurationError,
    UnconfiguredUsageWarning,
)
from ..Types.Options import PathResolutionSetting, PresetOptions, TracebackOptions


@SingletonClass
class SparkLogger(logging.Logger):
    """
    Singleton logger with explicit configuration and freeze semantics.

    Lifecycle:
        import → configure → freeze → use

    Invariant:
        Once configured, logging behavior is immutable for the lifetime
        of the logger instance.
    """

    def __init__(self) -> None:
        super().__init__("LogSpark")
        self._lock = threading.RLock()
        self._config: LoggerConfig | None = None
        self._frozen = False
        self._stdlib_logger: logging.Logger | None = None
        self._pre_config_setup_done = False
        self._unconfigured_warning_emitted = False
        self._logger_name = "LogSpark"

        self._ensure_pre_config_setup()

    @property
    def is_frozen(self) -> bool:
        """
        Check if the logger configuration is frozen (immutable).

        Returns:
            True if the logger has been configured and frozen, False otherwise.

        Note:
            Once configure() is called, the logger is automatically frozen and
            this method will always return True.
        """
        return self._frozen

    @property
    def config(self) -> LoggerConfig:
        if self._config is None:
            raise InvalidConfigurationError("LogSpark logger not configured")
        return self._config

    # PUBLIC LOGGING API
    def debug(self, msg: object, *args: object, **kwargs: Any) -> None:
        """
        Log a message with severity 'DEBUG'.

        Args:
            msg: The message to log. Can be any object that will be converted to string.
            *args: Arguments for string formatting if msg contains format specifiers.
            **kwargs: Additional keyword arguments passed to the underlying logging call.
                     Common kwargs include 'extra' for additional context fields.

        Note:
            If the logger hasn't been configured, this will emit a suppressible warning
            and use minimal terminal logging.
        """
        self._ensure_config()
        self._log_with_callsite(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: object, *args: object, **kwargs: Any) -> None:
        """
        Log a message with severity 'INFO'.

        Args:
            msg: The message to log. Can be any object that will be converted to string.
            *args: Arguments for string formatting if msg contains format specifiers.
            **kwargs: Additional keyword arguments passed to the underlying logging call.
                     Common kwargs include 'extra' for additional context fields.

        Note:
            If the logger hasn't been configured, this will emit a suppressible warning
            and use minimal terminal logging.
        """
        self._ensure_config()
        self._log_with_callsite(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: object, *args: object, **kwargs: Any) -> None:
        """
        Log a message with severity 'WARNING'.

        Args:
            msg: The message to log. Can be any object that will be converted to string.
            *args: Arguments for string formatting if msg contains format specifiers.
            **kwargs: Additional keyword arguments passed to the underlying logging call.
                     Common kwargs include 'extra' for additional context fields.

        Note:
            If the logger hasn't been configured, this will emit a suppressible warning
            and use minimal terminal logging.
        """
        self._ensure_config()
        self._log_with_callsite(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: object, *args: object, **kwargs: Any) -> None:
        """
        Log a message with severity 'ERROR'.

        Args:
            msg: The message to log. Can be any object that will be converted to string.
            *args: Arguments for string formatting if msg contains format specifiers.
            **kwargs: Additional keyword arguments passed to the underlying logging call.
                     Common kwargs include 'extra' for additional context fields.

        Note:
            If the logger hasn't been configured, this will emit a suppressible warning
            and use minimal terminal logging.
        """
        self._ensure_config()
        self._log_with_callsite(logging.ERROR, msg, *args, **kwargs)

    def critical(self, msg: object, *args: object, **kwargs: Any) -> None:
        """
        Log a message with severity 'CRITICAL'.

        Args:
            msg: The message to log. Can be any object that will be converted to string.
            *args: Arguments for string formatting if msg contains format specifiers.
            **kwargs: Additional keyword arguments passed to the underlying logging call.
                     Common kwargs include 'extra' for additional context fields.

        Note:
            If the logger hasn't been configured, this will emit a suppressible warning
            and use minimal terminal logging.
        """
        self._ensure_config()
        self._log_with_callsite(logging.CRITICAL, msg, *args, **kwargs)

    def exception(self, msg: object, *args: object, **kwargs: Any) -> None:
        """
        Log a message with severity 'ERROR', including exception information.

        This method should be called from within an except block.
        It is equivalent to calling error(..., exc_info=True).

        Args:
            msg: The message to log. Can be any object that will be converted to string.
            *args: Arguments for string formatting if msg contains format specifiers.
            **kwargs: Additional keyword arguments passed to the underlying logging call.
                      'exc_info' will always be set to True.
        """
        self._ensure_config()
        kwargs.setdefault("exc_info", True)
        self._log_with_callsite(logging.ERROR, msg, *args, **kwargs)

    def log(self, level: int, msg: object, *args: object, **kwargs: Any) -> None:
        """
        Log a message at an explicit numeric severity level.

        This method exists for compatibility with generic logging utilities
        and tooling that operate on numeric log levels and expect a `log()`
        entry point, mirroring the standard library logging.Logger API.

        preserves all LogSpark invariants:
          - explicit configuration and freeze semantics
          - deterministic callsite resolution
          - controlled handler and traceback policy enforcement
        """
        self._ensure_config()
        self._log_with_callsite(level, msg, *args, **kwargs)

    # PUBLIC SETTINGS API
    def configure(
        self,
        level: str | int = logging.INFO,
        *,
        handler: logging.Handler | PresetOptions = PresetOptions.TERMINAL,
        traceback_policy: TracebackOptions | None = TracebackOptions.COMPACT,
        path_resolution: PathResolutionSetting | None = PathResolutionSetting.RELATIVE,
        no_freeze: bool = False,
    ) -> None:
        with self._lock:
            if self._frozen:
                raise FrozenConfigurationError("Cannot configure logger after freeze")

            log_level = validate_level(level)

            # Default to TerminalHandler if none provided
            if is_fast_mode() and isinstance(handler, PresetOptions):
                # Fast logging with no explicit handler - use NullHandler for maximum speed
                hdl: logging.Handler = logging.NullHandler()
            elif isinstance(handler, PresetOptions):
                hdl = self._get_preset_handler(handler, traceback_policy, path_resolution)
            else:
                hdl = handler

            # Create configuration
            config = LoggerConfig(
                level=log_level,
                handler=hdl,
                traceback_policy=traceback_policy,
                path_resolution=path_resolution,
            )

            self._config = config

            # Clear existing handlers but preserve filters (including ddtrace)
            self._eject_handlers()

            self.setLevel(config.level)
            self.addHandler(config.handler)

            # Ensure ddtrace filter is present (idempotent)
            self._add_dd_stage()

            # Automatically freeze configuration after successful configure
            if no_freeze:
                return

            self._frozen = True

    def _eject_handlers(self) -> None:
        for _handler in self.handlers:
            _handler.flush()
            _handler.close()
        self.handlers.clear()

    @staticmethod
    def _get_preset_handler(
        preset: PresetOptions,
        traceback: TracebackOptions | None,
        path_resolution: PathResolutionSetting | None,
    ) -> logging.Handler:
        # if handler is none but handler_preset isn't we apply the handler_preset
        _handler: logging.Handler | None = None
        if preset == PresetOptions.TERMINAL or preset is None:
            from .._Internal.State import is_rich_available

            if is_rich_available():
                from ..Handlers.Rich.RichHandler import RichHandler

                _handler = RichHandler()
            else:
                from ..Handlers import TerminalHandler

                _handler = TerminalHandler()
        elif preset == PresetOptions.JSON:
            from ..Handlers import JsonHandler

            _handler = JsonHandler()
        else:
            # invalid handler_preset
            raise ValueError(f"Invalid handler_preset '{preset}'")
        assert _handler is not None
        if traceback is not None:
            _t_filter: TracebackPolicy = TracebackPolicy()
            _t_filter.configure(traceback_policy=traceback)
            # If we use our own handler we know we own the downstream so injection is safe
            _t_filter.set_injection(True)
            _handler.addFilter(_t_filter)
        if path_resolution is not None:
            _p_filter: PathNormalization = PathNormalization()
            _p_filter.configure(path_resolution_mode=path_resolution)
            _p_filter.set_injection(True)
            _handler.addFilter(_p_filter)
        return _handler

    def _add_dd_stage(self) -> None:
        # Ddtrace is global so to prevent duplication we handle it at the logger state not the handler state
        if is_ddtrace_available():
            has_ddtrace_filter = any(isinstance(f, DDTraceInjection) for f in self.filters)
            if not has_ddtrace_filter:
                log_filter = DDTraceInjection()
                self.addFilter(log_filter)

    def freeze(self) -> None:
        if self._frozen:
            return

        if self._config is None:
            raise InvalidConfigurationError(
                "The logger has to be configured by calling configure(...) before you can freeze it."
            )

        self._frozen = True

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
            for h in self.handlers[:]:
                self.removeHandler(h)
                h.close()

            logging.Logger.manager.loggerDict.pop(name, None)

            # Reset instance state
            self._config = None
            self._frozen = False
            self._pre_config_setup_done = False
            self._unconfigured_warning_emitted = False

            # Intentionally do not reset Singleton slot
            # this maintans the relationship between singleton and
            # the global logging registry

    # INTERNAL
    def _log_with_callsite(self, level: int, msg: object, *args: object, **kwargs: Any) -> None:
        # Get user-provided stacklevel or default
        user_stacklevel = kwargs.get("stacklevel", 1)

        # Resolve appropriate stacklevel to point to actual calling code
        resolved_stacklevel = resolve_stacklevel(user_stacklevel)
        kwargs["stacklevel"] = resolved_stacklevel

        self.log(level, msg, *args, **kwargs)

    def _ensure_config(self) -> None:
        if self._config is None:
            self._emit_unconfigured_warning()
            self._ensure_pre_config_setup()

    def _ensure_pre_config_setup(self) -> None:
        if self._pre_config_setup_done:
            return

        with self._lock:
            # Create stdlib logger with LogSpark defaults
            if self.handlers:
                self._raise_logger_name_conflict()
                return

            self.setLevel(logging.INFO)
            # Detect stdlib handler as fallback
            handler = PreConfigHandler()
            self.addHandler(handler)

            self._pre_config_setup_done = True

    def _emit_unconfigured_warning(self) -> None:
        if not self._unconfigured_warning_emitted:
            emit_warning(
                message="\nWARNING: Logger used before configuration.\n"
                "  | This warning indicates a lifecycle violation;\n"
                "  | call logger.configure() before logging",
                category=UnconfiguredUsageWarning,
                stacklevel=4,
            )
            self._unconfigured_warning_emitted = True

    def _raise_logger_name_conflict(self) -> None:
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
                "  | Ensure logging is configured exactly once, early in process startup,\n"
                "  | before any threads, workers, or process pools are created.\n"
                "  | No other code may create or configure this logger name.\n"
            ).format(name=self._logger_name)
        )
