#  Copyright (c) 2025.
#  Author: Willem van der Schans.
#  Licensed under the MIT License (https://opensource.org/license/mit).
import logging
from datetime import datetime
from pathlib import Path
from typing import IO, TYPE_CHECKING, cast

from rich._log_render import FormatTimeCallable
from rich.console import Console, ConsoleRenderable
from rich.highlighter import Highlighter
from rich.logging import RichHandler as _RichHandler
from rich.traceback import Traceback

from ..._Internal import _DegradationGates
from ..._Internal.Func import (
    emit_color_incompatible_rich_console_warning,
    emit_warning,
    is_color_compatible_terminal,
    resolve_stream,
)
from ...Filters.PathNormalization import SupportsResolvedPath
from ...Formatters.Rich.SparkRichFormatter import SparkRichFormatter
from ...Types import InvalidConfigurationError
from ...Types.Options import SparkRichHandlerSettings
from ...Types.Protocol import SupportsWrite

if TYPE_CHECKING:
    from rich._log_render import FormatTimeCallable
    from rich.console import Console


class RichHandler(_RichHandler):
    """
    Enhanced Rich logging handler with customizable layout and rendering.

    Extends Rich's RichHandler with LogSpark-specific features including:
    - Configurable column widths and display options
    - Custom log rendering with budget-based layout
    - Enhanced path resolution and function name display
    - Flexible time formatting and level display

    This handler uses a SparkRichFormatter for structured, terminal-aware output
    that adapts to available screen space while maintaining readability.

    Args:
        level: Minimum log level to handle
        console: Optional Rich Console instance for output
        min_message_width: Minimum width reserved for log messages (default: 60)
        markup: Whether to enable Rich markup in log messages (default: False)
        rich_tracebacks: Whether to use Rich's enhanced traceback formatting (default: True)
        highlighter: Optional Rich Highlighter for syntax highlighting
        show_time: Whether to display timestamps (default: True)
        log_time_format: Time format string or callable (default: "%H:%M:%S")
        omit_repeated_times: Whether to hide repeated timestamps (default: True)
        show_level: Whether to display log levels (default: True)
        level_width: Fixed width for level column (default: 8)
        show_path: Whether to display source file paths (default: True)
        max_path_width: Maximum width for path column (default: 40)
        show_function: Whether to display function names (default: False)
        max_function_width: Maximum width for function column (default: 25)
        tracebacks_width: Optional width limit for tracebacks
        tracebacks_extra_lines: Extra context lines in tracebacks (default: 3)
    """

    _warn_width_shown: bool = False

    def __init__(
        self,
        level: int | str = logging.NOTSET,
        console: Console | None = None,
        stream: SupportsWrite | None = None,
        *,
        # Main Settings
        use_color: bool = True,
        highlighter: Highlighter | None = None,
        # Optional settings
        show_time: bool = True,
        show_level: bool = True,
        show_path: bool = True,
        show_function: bool = False,
        level_width: int = 8,
        log_time_format: "str | FormatTimeCallable" = "%H:%M:%S",
        # Advanced settings
        settings: SparkRichHandlerSettings | None = None,
    ) -> None:

        if console is None:
            from rich.console import Console

            spark_stream = resolve_stream(stream)
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

        if not use_color:
            from rich.highlighter import NullHighlighter

            highlighter = NullHighlighter()

        if settings is None:
            settings = SparkRichHandlerSettings()

        super().__init__(
            level,
            console,
            show_time=show_time,
            show_level=show_level,
            show_path=show_path,
            markup=False,
            rich_tracebacks=True,
            tracebacks_width=settings.tracebacks_width,
            tracebacks_extra_lines=settings.tracebacks_extra_lines,
            log_time_format=log_time_format,
            highlighter=highlighter,
            enable_link_path=settings.enable_link_path,
        )

        self._c_log_render: SparkRichFormatter = SparkRichFormatter(
            show_time=show_time,
            show_level=show_level,
            show_path=show_path,
            show_function=show_function,
            time_format=log_time_format,
            omit_repeated_times=settings.omit_repeated_times,
            level_width=level_width,
            max_path_width=settings.max_path_width,
            max_function_width=settings.max_function_width,
            min_message_width=settings.min_message_width,
            indent_guide=settings.indent_guide,
        )

    def render(
        self,
        *,
        record: logging.LogRecord,
        traceback: Traceback | None,
        message_renderable: "ConsoleRenderable",
    ) -> "ConsoleRenderable":
        """Render log for display.

        Args:
            record (LogRecord): logging Record.
            traceback (Optional[Traceback]): Traceback instance or None for no Traceback.
            message_renderable (ConsoleRenderable): Renderable (typically Text)
            containing log message contents.

        Returns:
            ConsoleRenderable: Renderable to display log.
        """
        # Resolve Path
        if isinstance(record, SupportsResolvedPath):
            display_path = record.resolved_path.path
            link_path = record.resolved_path.uri
            lineno = record.resolved_path.lineno
            func = record.resolved_path.function
        else:
            display_path = Path(record.pathname)
            link_path = None
            lineno = record.lineno
            func = record.funcName

        # Resolve Renderables
        renderables = [message_renderable]
        if traceback:
            renderables.append(traceback)
        # Resolve Time
        time_format, log_time = self._resolve_time(record.created)

        log_renderable = self._c_log_render(
            console=self.console,
            renderables=renderables,
            log_time=log_time,
            time_format=time_format,
            level=self.get_level_text(record),
            path=display_path,
            line_no=lineno,
            link_path=link_path,
            function_name=func,
        )

        if self._c_log_render.is_layout_degraded and not self._warn_width_shown:
            self._emit_degradation_warning()
        return log_renderable

    def _resolve_time(self, created: float) -> tuple[str | None, datetime]:
        if self.formatter is None:
            time_format = None
        else:
            time_format = self.formatter.datefmt
        return time_format, datetime.fromtimestamp(created)

    def _emit_degradation_warning(self) -> None:
        class ConsoleWidthWarning(UserWarning):
            """Warning emitted when found console size affects availability of layout elements"""

            pass

        cols_hidden = []

        if self._c_log_render.show_path and self._c_log_render._degradation_gate in (
            _DegradationGates.TIME,
            _DegradationGates.PATH,
        ):
            cols_hidden.append("Path")
        if self._c_log_render.show_function and self._c_log_render._degradation_gate in (
            _DegradationGates.TIME,
            _DegradationGates.PATH,
            _DegradationGates.FUNCTION,
        ):
            cols_hidden.append("Function")

        cols = ", ".join(cols_hidden)
        message = (
            "\nLogSpark layout degraded: \n"
            "  | terminal width ({width} cols) cannot satisfy the required message width ({message_width} cols)\n"
            "  | lower-priority metadata columns were hidden to preserve message readability: {cols}\n"
            "  | increase terminal width or reduce min_message_width to restore full layout."
        ).format(
            width=self.console.width, message_width=self._c_log_render.min_message_width, cols=cols
        )
        emit_warning(
            message=message,
            category=ConsoleWidthWarning,
            stacklevel=4,
        )
        self._warn_width_shown = True
