import logging
import sys
import traceback
from collections.abc import Callable
from logging import Filter
from types import TracebackType
from typing import IO, TYPE_CHECKING, Optional, cast

from .._Internal.Func import emit_console_warning, get_devnull, validate_level
from .._Internal.State import is_rich_available, is_silenced_mode, is_supported_terminal
from ..Types import InvalidConfigurationError, TracebackOptions
from ..Types.Protocol import SupportsWrite, _SupportsFilter

if TYPE_CHECKING:
    from rich.console import Console
    from rich.highlighter import NullHighlighter


class TerminalHandler(logging.Handler):
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
        show_time: bool = True,
        show_level: bool = True,
        show_path: bool = True,
        show_function: bool = False,
        use_color: bool = True,
        no_rich: bool = False,
        console: Optional["Console"] = None,
    ) -> None:
        """
        Initialize a terminal logging handler.

        Args:
            stream:
                Output stream for log records. Defaults to ``sys.stdout`` when
                Rich is used. Must implement a ``write(str)`` method.
            show_time:
                Whether to display a timestamp in log output.
            show_level:
                Whether to display the log level.
            show_path:
                Whether to display the source file and line number.
            show_function:
                Whether to display the calling function name.
            console:
                Optional pre-configured Rich ``Console`` instance. If provided,
                ``stream`` must not be set.

        Behavior:
            - If Rich is available, a Rich-backed handler is created.
            - If Rich is not available, output is delegated to a standard
              ``logging.StreamHandler``.
            - When no console is provided, terminal dimensions are inferred
              using ``shutil.get_terminal_size``. Zero-sized terminals fall
              back to conservative defaults.
            - TerminalHandler is stdout-oriented by design; stderr is never used implicitly

        Resolution order:
            1. If LOGSPARK_MODE is ``silenced``, output is discarded regardless
               of stream or console configuration.
            2. If a Rich Console is provided, ``stream`` must be None.
            3. If Rich is available and not disabled, rendering is delegated
               to SparkRichHandler.
            4. Otherwise, output falls back to a stdlib StreamHandler.

        Invariants:
            - stderr is never selected implicitly.
            - stdout is the default output stream when not silenced.
            - Console configuration always takes precedence over stream.

        Raises:
            InvalidConfigurationError:
                If both ``stream`` and ``console`` are provided.
        """

        # Rich is imported and user doesn't overwrite rich support
        if not no_rich:
            _use_rich = is_rich_available()
        else:
            _use_rich = False

        # Console override or console check passed
        if console is None:
            _use_console = is_supported_terminal()
        else:
            _use_console = True

        if _use_rich and not _use_console:
            emit_console_warning()

        if _use_rich and _use_console:
            from .._Internal.Intergration.SparkRichHandler import SparkRichHandler

            if console is None:
                from rich.console import Console

                spark_stream = self._resolve_stream(stream)
                spark_stream = cast(IO[str], spark_stream)
                console = Console(file=spark_stream, tab_size=4, no_color=not use_color)
            else:
                if stream is not None:
                    raise InvalidConfigurationError(
                        "Cannot set stream when passing in a pre-configured console."
                    )

            highlighter: "NullHighlighter | None" = None
            if not use_color:
                from rich.highlighter import NullHighlighter

                highlighter = NullHighlighter()

            self._handler: logging.Handler = SparkRichHandler(
                console=console,
                show_time=show_time,
                show_path=show_path,
                show_level=show_level,
                show_function=show_function,
                markup=False,  # Disable markup to prevent injection
                rich_tracebacks=True,  # Rich handles traceback formatting
                tracebacks_show_locals=False,  # Keep tracebacks focused
                log_time_format="[%H:%M:%S]",
                highlighter=highlighter,
            )
        else:
            # Rich not available - fall back to stdlib StreamHandler
            spark_stream = self._resolve_stream(stream)
            self._handler = logging.StreamHandler(stream=spark_stream)

            fmt = logging.Formatter(
                fmt="%(asctime)-8s - %(levelname)-8s - %(filename)s:%(lineno)d -> %(message)s",
                datefmt="[%H:%M:%S]",
            )

            self._handler.setFormatter(fmt)

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
                            f'File "{last_frame.filename}", '
                            f"line {last_frame.lineno}, "
                            f"in {last_frame.name}"
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
