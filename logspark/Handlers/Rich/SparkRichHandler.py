#  Copyright (c) 2025.
#  Author: Willem van der Schans.
#  Licensed under the MIT License (https://opensource.org/license/mit).
import logging
import os
import warnings
from datetime import datetime
from pathlib import Path

from rich._log_render import FormatTimeCallable
from rich.console import Console, ConsoleRenderable
from rich.highlighter import Highlighter
from rich.logging import RichHandler
from rich.traceback import Traceback

from ...Formatters.Rich.SparkRichLogRenderer import SparkRichLogRenderer

PYTHONPATH = os.environ.get("PYTHONPATH", None)
PYTHONPATH = PYTHONPATH.split(";")[0] if PYTHONPATH else None


class SparkRichHandler(RichHandler):
    """
    Enhanced Rich logging handler with customizable layout and rendering.

    Extends Rich's RichHandler with LogSpark-specific features including:
    - Configurable column widths and display options
    - Custom log rendering with budget-based layout
    - Enhanced path resolution and function name display
    - Flexible time formatting and level display

    This handler uses a SparkRichLogRenderer for structured, terminal-aware output
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
        *,
        # Main Settings
        min_message_width: int = 60,
        markup: bool = False,
        rich_tracebacks: bool = True,
        highlighter: Highlighter | None = None,
        # Time settings
        show_time: bool = True,
        log_time_format: str | FormatTimeCallable = "%H:%M:%S",
        omit_repeated_times: bool = True,
        # Level Settings
        show_level: bool = True,
        level_width: int = 8,
        # Path Settings
        show_path: bool = True,
        max_path_width: int = 40,
        # Function Settings
        show_function: bool = False,
        max_function_width: int = 25,
        # Traceback Settings
        tracebacks_width: int | None = None,
        tracebacks_extra_lines: int = 3,
    ) -> None:
        super().__init__(
            level,
            console,
            show_time=show_time,
            show_level=show_level,
            show_path=show_path,
            markup=markup,
            rich_tracebacks=rich_tracebacks,
            tracebacks_width=tracebacks_width,
            tracebacks_extra_lines=tracebacks_extra_lines,
            log_time_format=log_time_format,
            highlighter=highlighter,
        )
        self._c_log_render: SparkRichLogRenderer = SparkRichLogRenderer(
            show_time=show_time,
            show_level=show_level,
            show_path=show_path,
            show_function=show_function,
            time_format=log_time_format,
            omit_repeated_times=omit_repeated_times,
            level_width=level_width,
            max_path_width=max_path_width,
            max_function_width=max_function_width,
            min_message_width=min_message_width,
        )
        self._show_path: bool = show_path
        self._show_function: bool = show_function

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
        path = Path(record.pathname)
        log_path = None
        if PYTHONPATH is not None:
            try:
                rel = path.relative_to(PYTHONPATH)
                if len(rel.parts) > 1:
                    log_path = Path(*rel.parts[1:]).as_posix()
                else:
                    log_path = rel.as_posix()
            except ValueError:
                pass

        if log_path is None:
            if len(path.parts) > 2:
                log_path = Path(*path.parts[-2:]).as_posix()
            else:
                log_path = path.as_posix()

        if not path.is_absolute() or not self.enable_link_path:
            link_path = None
        else:
            link_path = Path(path).as_uri()

        # Resolve Renderables
        if traceback:
            renderables = [message_renderable, traceback]
        else:
            renderables = [message_renderable]

        # Resolve Time
        if self.formatter is None:
            time_format = None
        else:
            time_format = self.formatter.datefmt

        level = self.get_level_text(record)
        log_time = datetime.fromtimestamp(record.created)
        function_name = record.funcName

        log_renderable = self._c_log_render(
            console=self.console,
            renderables=renderables,
            log_time=log_time,
            time_format=time_format,
            level=level,
            path=str(log_path),
            line_no=record.lineno,
            link_path=link_path,
            function_name=function_name,
        )

        if self._c_log_render.is_layout_degraded and not self._warn_width_shown:
            self._emit_degradation_warning()

        return log_renderable

    def _emit_degradation_warning(self) -> None:
        class ConsoleWidthWarning(UserWarning):
            """Warning emitted when found console size affects availability of layout elements"""

            pass

        cols_hidden = []
        if self._c_log_render.show_path:
            cols_hidden.append("Path")
        if self._c_log_render.show_function:
            cols_hidden.append("Function")
        cols = ", ".join(cols_hidden)
        message = (
            "\nLogSpark layout degraded: terminal width ({width} cols) is smaller than minimum message width (80 cols). "
            "    Optionally selected metadata columns were hidden: {cols}"
            "    Adjust column settings or increase terminal width to restore full layout."
        ).format(width=self.console.width, cols=cols)
        warnings.warn(
            message=message,
            category=ConsoleWidthWarning,
            stacklevel=2,
            source="LogSpark",
        )
        self._warn_width_shown = True
