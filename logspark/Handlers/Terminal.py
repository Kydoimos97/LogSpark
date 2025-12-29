import logging
import sys
import traceback
from logging import Filter
from types import TracebackType
from typing import Optional, Union, Callable, cast, IO, TYPE_CHECKING

from ..Internal.Func.env import (
    emit_console_warning,
    is_supported_terminal,
    get_devnull,
    is_silenced_mode,
)
from ..Types import InvalidConfigurationError, TracebackOptions
from ..Types.Protocol import SupportsWrite, _SupportsFilter

if TYPE_CHECKING:
    from rich.console import Console
    from rich.text import Text

RICH_TEXT: Optional[type["Text"]] = None
RICH_CONSOLE: Optional[type["Console"]] = None

try:
    # noinspection PyUnresolvedReferences
    from rich.console import Console

    # noinspection PyUnresolvedReferences
    from rich.text import Text

    RICH_CONSOLE = Console
    RICH_TEXT = Text
    if not is_supported_terminal():
        emit_console_warning()
        RICH_TEXT = None
        RICH_CONSOLE = None
except ImportError:
    pass


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

    Example:
        ```python
        from logspark import logger
        from logspark.handlers import TerminalHandler
        from logspark.Types import TracebackOptions

        logger.configure(
            level=logging.DEBUG,
            handler=TerminalHandler(show_function=True),
            traceback=TracebackOptions.COMPACT,
        )

        logger.info("Application started")
        logger.error("Something went wrong", exc_info=True)
        ```
    """

    _use_rich = False if RICH_TEXT is None else True

    def __init__(
        self,
        stream: Optional[SupportsWrite] = None,
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

        Raises:
            InvalidConfigurationError:
                If both ``stream`` and ``console`` are provided.
        """
        # Detect Rich availability and create appropriate handler
        if self._use_rich and not no_rich:
            from ..Internal.Hooks.SparkRichHandler import SparkRichHandler
            from rich.highlighter import NullHighlighter

            if console is None:
                spark_stream = self._resolve_stream(stream)
                spark_stream = cast(IO[str], spark_stream)
                console = Console(file=spark_stream, tab_size=4, no_color=not use_color)
            else:
                if stream is not None:
                    raise InvalidConfigurationError(
                        f"Cannot set stream when passing in a pre-configured console."
                    )

            highlighter: Optional[NullHighlighter] = None
            if not use_color:
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
            exc_type: Optional[type[BaseException]] = record.exc_info[0]
            exc_value: Optional[BaseException] = record.exc_info[1]
            tb: Optional[TracebackType] = record.exc_info[2]
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

    def setLevel(self, level: Union[int, str]) -> None:
        """Set level on both this handler and composed handler"""
        super().setLevel(level)
        self._handler.setLevel(level)

    # noinspection PyShadowingBuiltins
    def addFilter(
        self, filter: Union[Filter, Callable[[logging.LogRecord], bool], _SupportsFilter]
    ) -> None:
        """Add filter to both this handler and composed handler"""
        super().addFilter(filter)
        self._handler.addFilter(filter)

    # noinspection PyShadowingBuiltins
    def removeFilter(
        self, filter: Union[Filter, Callable[[logging.LogRecord], bool], _SupportsFilter]
    ) -> None:
        """Remove filter from both this handler and composed handler"""
        super().removeFilter(filter)
        self._handler.removeFilter(filter)

    @staticmethod
    def _resolve_stream(stream: Optional[SupportsWrite]) -> SupportsWrite:
        stream = stream or sys.stdout
        if is_silenced_mode():
            stream = get_devnull()
        return stream
