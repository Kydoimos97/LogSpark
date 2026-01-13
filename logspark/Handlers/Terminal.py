import logging
import sys
import traceback
from collections.abc import Callable
from logging import Filter
from types import TracebackType
from typing import IO, TYPE_CHECKING, Optional, cast

from .._Internal.Func import (
    emit_color_incompatible_console_warning,
    emit_color_incompatible_rich_console_warning,
    generate_stdlib_format,
    get_devnull,
    is_color_compatible_terminal,
    validate_level,
    validate_rich_timeformat,
    validate_stdlib_timeformat,
)
from .._Internal.State import is_rich_available, is_silenced_mode
from ..Types import InvalidConfigurationError, TracebackOptions
from ..Types.Protocol import SupportsWrite, _SupportsFilter

if TYPE_CHECKING:
    from rich._log_render import FormatTimeCallable
    from rich.console import Console
    from rich.highlighter import NullHighlighter


class SparkTerminalHandler(logging.Handler):
    """
    Human-readable terminal logging handler with optional Rich rendering.

    This handler targets interactive, developer-facing output. When Rich is
    available, it delegates rendering to a Rich-based handler for structured
    layout, colors, and enhanced tracebacks. When Rich is not available, it
    falls back to a standard ``logging.StreamHandler``.

    The handler is implemented as a *composed handler*: it wraps an internal
    handler instance and forwards log records after applying LogSpark-specific
    policies such as traceback formatting.

    Features:
        - Optional Rich-enhanced terminal output
        - Graceful fallback to stdlib StreamHandler when Rich is unavailable
        - Configurable display of time, level, path, and function name
        - Traceback rendering controlled via ``TracebackOptions``
        - Automatic terminal size detection with conservative defaults

    Traceback handling:
        The handler inspects the ``traceback_policy`` attribute on log records.
        Depending on the policy, exception information may be suppressed,
        compacted, or fully rendered by Rich.

    Console configuration:
        A pre-configured Rich ``Console`` may be supplied directly. When a
        console is provided, the ``stream`` argument must not be set.

    Intended use:
        This handler is designed for human-readable output during development
        and interactive use. It is not intended for high-volume or structured
        logging pipelines.
    """

    def __init__(
        self,
        stream: SupportsWrite | None = None,
        *,
        use_color: bool = True,
        no_rich: bool = False,
        console: Optional["Console"] = None,
        # Main Settings
        min_message_width: int = 40,
        rich_tracebacks: bool = True,
        # Time settings
        show_time: bool = True,
        log_time_format: "str | FormatTimeCallable | None" = "%H:%M:%S",
        omit_repeated_times: bool = True,
        # Level Settings
        show_level: bool = True,
        level_width: int = 8,
        # Path Settings
        show_path: bool = True,
        relative_path: bool = False,
        enable_link_path: bool = True,
        max_path_width: int = 40,
        # Function Settings
        show_function: bool = False,
        max_function_width: int = 25,
        # Traceback Settings
        tracebacks_width: int | None = None,
        tracebacks_extra_lines: int = 3,
    ) -> None:
        """
        Initialize a terminal logging handler.

        Args:
            stream: Output stream for log records. Defaults to sys.stdout when
                Rich is used. Must implement a write(str) method.
            use_color: Whether to enable colored output (default: True)
            no_rich: Whether to disable Rich rendering and use stdlib handler (default: False)
            console: Optional pre-configured Rich Console instance. If provided,
                stream must not be set.
            min_message_width: Minimum width reserved for log messages (default: 60)
            rich_tracebacks: Whether to use Rich's enhanced traceback formatting (default: True)
            show_time: Whether to display timestamps (default: True)
            log_time_format: Time format string or callable (default: "[%H:%M:%S]")
            omit_repeated_times: Whether to hide repeated timestamps (default: True)
            show_level: Whether to display log levels (default: True)
            level_width: Fixed width for level column (default: 8)
            show_path: Whether to display source file paths (default: True)
            max_path_width: Maximum width for path column (default: 40)
            show_function: Whether to display function names (default: False)
            max_function_width: Maximum width for function column (default: 25)
            tracebacks_width: Optional width limit for tracebacks
            tracebacks_extra_lines: Extra context lines in tracebacks (default: 3)

        Behavior:
            - If Rich is available, a Rich-backed handler is created.
            - If Rich is not available, output is delegated to a standard
              logging.StreamHandler.
            - When no console is provided, terminal dimensions are inferred
              using shutil.get_terminal_size. Zero-sized terminals fall
              back to conservative defaults.
            - SparkTerminalHandler is stdout-oriented by design; stdout is the default stream

        Resolution order:
            1. If LOGSPARK_MODE is silenced, output is discarded regardless
               of stream or console configuration.
            2. If a Rich Console is provided, stream must be None.
            3. If Rich is available and not disabled, rendering is delegated
               to SparkRichHandler.
            4. Otherwise, output falls back to a stdlib StreamHandler.

        Invariants:
            - stdout is the default output stream when not silenced.
            - Console configuration always takes precedence over stream.

        Raises:
            InvalidConfigurationError:
                If both stream and console are provided.
        """

        # Initialize handler to None
        _handler: logging.Handler | None = None

        # Rich is imported and user doesn't overwrite rich support
        if not no_rich:
            _use_rich = is_rich_available()
        else:
            _use_rich = False

        if _use_rich:
            rich_time_format = validate_rich_timeformat(log_time_format)
            if console is None:
                from rich.console import Console

                spark_stream = self._resolve_stream(stream)
                spark_stream = cast(IO[str], spark_stream)
                _compatible = is_color_compatible_terminal(spark_stream)
                # Force Behavior when color support is detected
                if _compatible:
                    console = Console(
                        file=spark_stream,
                        tab_size=4,
                        no_color=not use_color,
                        color_system="truecolor",
                        force_terminal=True,
                        legacy_windows=False,
                    )
                    # Force initial truecolor fallback then run validation as compatibility
                    color_system = console._detect_color_system()
                    if color_system is not None:
                        console._color_system = color_system
                else:
                    console = Console(file=spark_stream, tab_size=4, no_color=not use_color)
            else:
                if stream is not None:
                    raise InvalidConfigurationError(
                        "Cannot set stream when passing in a pre-configured console."
                    )

            if not is_color_compatible_terminal(console.file) and use_color:
                emit_color_incompatible_rich_console_warning()

            # Set Highlighter
            highlighter: "NullHighlighter | None" = None
            if not use_color:
                from rich.highlighter import NullHighlighter

                highlighter = NullHighlighter()

            from ..Handlers.Rich.SparkRichHandler import SparkRichHandler

            _handler = SparkRichHandler(
                # Main Settings
                console=console,  # Keep tracebacks focused
                log_time_format=rich_time_format,
                highlighter=highlighter,
                min_message_width=min_message_width,
                markup=False,  # Disable markup to prevent injection
                rich_tracebacks=rich_tracebacks,  # Rich handles traceback formatting
                # Time settings
                show_time=show_time,
                omit_repeated_times=omit_repeated_times,
                # Level Settings
                show_level=show_level,
                level_width=level_width,
                # Path Settings
                show_path=show_path,
                relative_path = relative_path,
                enable_link_path = enable_link_path,
                max_path_width=max_path_width,
                # Function Settings
                show_function=show_function,
                max_function_width=max_function_width,
                # Traceback Settings
                tracebacks_width=tracebacks_width,
                tracebacks_extra_lines=tracebacks_extra_lines,
            )

        if _handler is None:
            # Rich not available - fall back to stdlib StreamHandler
            std_lib_time_format = validate_stdlib_timeformat(log_time_format)
            spark_stream = self._resolve_stream(stream)
            _handler = logging.StreamHandler(stream=spark_stream)
            fmt: logging.Formatter | None = None
            fmt_string = generate_stdlib_format(
                show_time=show_time,
                show_level=show_level,
                level_width=level_width,
                show_path=show_path,
                show_function=show_function,
            )
            _compatible = is_color_compatible_terminal(spark_stream)
            if use_color:
                # Don't pass the console as we aren't checking rich
                if _compatible:
                    from ..Formatters import SparkColorFormatter

                    fmt = SparkColorFormatter(
                        fmt=fmt_string,
                        datefmt=std_lib_time_format,
                    )
                else:
                    emit_color_incompatible_console_warning()

            if fmt is None:
                fmt = logging.Formatter(
                    fmt=fmt_string,
                    datefmt=std_lib_time_format,
                )

            _handler.setFormatter(fmt)

        self._handler = _handler

        # Initialize parent Handlers
        super().__init__()

        # Copy level and filters from composed handler
        self.setLevel(self._handler.level)

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit log record using composed handler

        Args:
            record: LogRecord to emit
        """
        # Handle traceback policy for terminal output consistency
        if record.exc_info:
            exc_type: type[BaseException] | None = record.exc_info[0]
            exc_value: BaseException | None = record.exc_info[1]
            tb: TracebackType | None = record.exc_info[2]
            traceback_policy = getattr(record, "traceback_policy", TracebackOptions.NONE)

            if traceback_policy == TracebackOptions.NONE or exc_type is None or exc_value is None:
                # Remove exception info to prevent traceback inclusion
                record.exc_info = None
                record.exc_text = None
            elif traceback_policy == TracebackOptions.COMPACT:
                # Format compact traceback for terminal display
                try:
                    tb_frames = traceback.extract_tb(tb)
                    if tb_frames:
                        last_frame = tb_frames[-1]
                        compact_tb = (
                            f"{exc_type.__name__}: {exc_value}\n  "
                            f'    File "{last_frame.filename}", '
                            f"    line {last_frame.lineno}, "
                            f"    in {last_frame.name}"
                        )
                    else:
                        compact_tb = f"{exc_type.__name__}: {exc_value}"

                    record.exc_text = compact_tb
                except Exception:
                    # Fallback if traceback processing fails
                    record.exc_text = f"{exc_type.__name__}: {exc_value}"

                record.exc_info = None  # Prevent default Rich traceback formatting
            # For FULL policy, let Rich handle the full traceback (default behavior)

        self._handler.emit(record)

    def setLevel(self, level: int | str) -> None:
        """Set level on both this handler and composed handler"""
        level_int = validate_level(level)
        super().setLevel(level_int)
        self._handler.setLevel(level_int)

    # noinspection PyShadowingBuiltins
    def addFilter(
        self, filter: Filter | Callable[[logging.LogRecord], bool] | _SupportsFilter
    ) -> None:
        """Add filter to both this handler and composed handler"""
        super().addFilter(filter)
        self._handler.addFilter(filter)

    # noinspection PyShadowingBuiltins
    def removeFilter(
        self, filter: Filter | Callable[[logging.LogRecord], bool] | _SupportsFilter
    ) -> None:
        """Remove filter from both this handler and composed handler"""
        super().removeFilter(filter)
        self._handler.removeFilter(filter)

    @staticmethod
    def _resolve_stream(stream: SupportsWrite | None) -> SupportsWrite:
        stream = stream or sys.stdout
        if is_silenced_mode():
            stream = get_devnull()
        return stream
