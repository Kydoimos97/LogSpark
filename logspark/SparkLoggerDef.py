import logging
import threading
import warnings
from typing import Any

from ._Internal.Func import (
    configure_handler_traceback_policy,
    resolve_stacklevel,
    validate_configuration_parameters,
)
from ._Internal.State import LoggerConfig, SingletonClass, is_fast_mode
from .Filters.DDTraceCorrelationFilter import DDTraceCorrelationFilter
from .Handlers.PreConfig import pre_config_handler
from .Types import (
    FrozenConfigurationError,
    InvalidConfigurationError,
    PresetOptions,
    TracebackOptions,
)
from .Types.Exceptions import UnconfiguredUsageWarning


@SingletonClass
class SparkLogger:
    """
    Singleton logger with explicit configuration and freeze semantics.

    Lifecycle:
        import → configure → freeze → use

    Invariant:
        Once configured, logging behavior is immutable for the lifetime
        of the logger instance.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._config: LoggerConfig | None = None
        self._frozen = False
        self._stdlib_logger: logging.Logger | None = None
        self._pre_config_setup_done = False
        self._unconfigured_warning_emitted = False

    # PROPERTIES
    @property
    def instance(self) -> logging.Logger:
        """
        Access the underlying standard library Logger instance.

        Returns:
            The stdlib logging.Logger instance that backs this LogSpark logger.

        Note:
            This provides direct access to the stdlib logger for advanced use cases
            or integration with existing logging infrastructure. The returned logger
            is fully configured and ready for use.
        """
        if self._stdlib_logger is None:
            self._ensure_pre_config_setup()
        assert self._stdlib_logger is not None
        return self._stdlib_logger

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

    # PUBLIC SETTINGS API
    def configure(
        self,
        level: str | int = logging.INFO,
        *,
        traceback: TracebackOptions | str | None = TracebackOptions.COMPACT,
        handler: logging.Handler | None = None,
        preset: PresetOptions | str | None = None,
        no_freeze: bool = False,
    ) -> None:
        """
        Configure the logger with handler-based configuration and automatically freeze it.

        This method sets up the logger's behavior and immediately locks the configuration
        to prevent further changes. Once called, the logger is ready for use.

        Args:
            level: Standard library logging level (e.g., logging.INFO, logging.DEBUG).
                Controls which messages are processed based on severity.

            handler: Custom stdlib Handlers instance that defines transport and formatting.
                When provided, this handler will be used regardless of preset settings.
                Must be a properly configured logging.Handlers subclass.

            traceback: Policy for including traceback information in log records.
                Can be a TracebackOptions enum value or a string:
                - TracebackOptions.NONE | None: No traceback information
                - TracebackOptions.COMPACT | "compact": Minimal traceback details
                - TracebackOptions.FULL | "full": Complete traceback information
                String values are case-insensitive.

            preset: Quick-reference logging preset for common use cases.
                Ignored when `handler` parameter is provided.

                Available presets:
                - PresetOptions.TERMINAL | "terminal": Human-readable terminal output with Rich formatting
                  when available, suitable for development and interactive use.
                - PresetOptions.JSON | "json": Structured JSON output for log aggregation and
                  production environments.

            no_freeze: If True, calling this method does not freeze the logger's configuration.

        Raises:
            FrozenConfigurationError: If configure() has already been called on this logger.
            InvalidConfigurationError: If any parameter values are invalid.

        Note:
            After calling configure(), the logger is automatically frozen and cannot be
            reconfigured. This ensures configuration consistency throughout the application
            lifecycle.

        Example:
            ```python
            from logspark import logger
            import logging

            # Basic configuration
            logger.configure(level=logging.DEBUG)

            # Production JSON logging
            logger.configure(
                level=logging.INFO,
                preset=PresetOptions.JSON,
                traceback=TracebackOptions.COMPACT
            )
            ```
        """
        with self._lock:
            if self._frozen:
                raise FrozenConfigurationError("Cannot configure logger after freeze")

            # Validate parameters before creating configuration
            v_level, v_traceback, v_preset = validate_configuration_parameters(
                level, traceback, handler, preset, no_freeze
            )

            # Default to TerminalHandler if none provided
            if is_fast_mode() and handler is None:
                # Fast logging with no explicit handler - use NullHandler for maximum speed
                fmt: logging.Handler = logging.NullHandler()
            elif handler is None and v_preset is not None:
                # if handler is none but preset isn't we apply the preset
                if v_preset == PresetOptions.TERMINAL:
                    from .Handlers import TerminalHandler

                    fmt = TerminalHandler()
                elif v_preset == PresetOptions.JSON:
                    from .Handlers import JSONHandler

                    fmt = JSONHandler()
                else:
                    # invalid preset
                    raise ValueError(f"Invalid preset '{preset}'")
            elif handler is None and v_preset is None:
                # both are none so we fall back to default
                from .Handlers import TerminalHandler

                fmt = TerminalHandler()
            else:
                # handler has been passed
                assert handler is not None
                fmt = handler

            # Create configuration
            config = LoggerConfig(level=v_level, handler=fmt, traceback_policy=v_traceback)

            self._config = config

            # Clear existing handlers but preserve filters (including ddtrace)
            self.instance.handlers.clear()
            self.instance.setLevel(config.level)

            # Configure handler with traceback policy
            configure_handler_traceback_policy(config.handler, config.traceback_policy)
            self.instance.addHandler(config.handler)

            # Ensure ddtrace filter is present (idempotent)
            # Check if filter already exists to avoid duplicates
            has_ddtrace_filter = any(
                isinstance(f, DDTraceCorrelationFilter) for f in self.instance.filters
            )
            if not has_ddtrace_filter:
                ddtrace_filter = DDTraceCorrelationFilter()
                self.instance.addFilter(ddtrace_filter)

            # Automatically freeze configuration after successful configure
            if no_freeze:
                return
            self._frozen = True

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
            if self._stdlib_logger is not None:
                self._stdlib_logger.handlers.clear()
                self._stdlib_logger.filters.clear()
                self._stdlib_logger.setLevel(logging.NOTSET)

            # Reset instance state
            self._config = None
            self._frozen = False
            self._stdlib_logger = None
            self._pre_config_setup_done = False
            self._unconfigured_warning_emitted = False

            # Reset singleton slot (critical)
            cls = self.__class__
            if hasattr(cls, "_SingletonWrapper__cls_instance"):
                cls._SingletonWrapper__cls_instance = None

    # INTERNAL
    def _log_with_callsite(self, level: int, msg: object, *args: object, **kwargs: Any) -> None:
        # Get user-provided stacklevel or default
        user_stacklevel = kwargs.get("stacklevel", 1)

        # Resolve appropriate stacklevel to point to actual calling code
        resolved_stacklevel = resolve_stacklevel(user_stacklevel)
        kwargs["stacklevel"] = resolved_stacklevel

        self.instance.log(level, msg, *args, **kwargs)

    def _ensure_config(self) -> None:
        if self._config is None:
            self._emit_unconfigured_warning()
            self._ensure_pre_config_setup()

    def _ensure_pre_config_setup(self) -> None:
        if self._pre_config_setup_done:
            return

        with self._lock:
            # Create stdlib logger with LogSpark defaults
            self._stdlib_logger = logging.getLogger("LogSpark")
            self._stdlib_logger.setLevel(logging.INFO)

            # Add ddtrace correlation filter for opportunistic field injection
            ddtrace_filter = DDTraceCorrelationFilter()
            self._stdlib_logger.addFilter(ddtrace_filter)

            # Detect stdlib handler as fallback
            handler = pre_config_handler()
            self._stdlib_logger.addHandler(handler)

            self._pre_config_setup_done = True

    def _emit_unconfigured_warning(self) -> None:
        if not self._unconfigured_warning_emitted:
            warnings.warn_explicit(
                message="\nLogger used before explicit configuration. \n"
                "    To remove this warning please call `logger.configure()",
                category=UnconfiguredUsageWarning,
                filename="SparkLoggerDef.py",
                lineno=446,
                module="LogSpark",
            )
            self._unconfigured_warning_emitted = True


spark_logger = SparkLogger()
