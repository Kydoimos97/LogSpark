#  Copyright (c) 2025.
#  Author: Willem van der Schans.
#  Licensed under the MIT License (https://opensource.org/license/mit).
from datetime import datetime
from logging import NOTSET, LogRecord
from pathlib import Path
from typing import IO, cast

from rich._log_render import FormatTimeCallable
from rich._null_file import NullFile
from rich.console import Console, ConsoleRenderable
from rich.highlighter import Highlighter
from rich.logging import RichHandler as _RichHandler
from rich.style import Style
from rich.styled import Styled
from rich.text import Text
from rich.traceback import Traceback

from ..._Internal.Func import (
    emit_color_incompatible_rich_console_warning,
    emit_warning,
    is_color_compatible_terminal,
    resolve_stream,
)
from ..._Internal.State.Env import get_console_width
from ...Formatters.Rich.SparkRichFormatter import SparkRichFormatter
from ...Formatters.SparkBaseFormatter import SparkBaseFormatMixin
from ...Types import InvalidConfigurationError
from ...Types.Options import SparkRichHandlerSettings, TracebackOptions
from ...Types.Protocol import SupportsWrite
from ...Types.SparkRecordAttrs import HasSparkAttributes


class SparkRichHandler(SparkBaseFormatMixin, _RichHandler):
    """
    Rich-based logging handler with budget-aware column layout.

    Extends ``rich.logging.RichHandler`` with LogSpark-specific rendering via
    ``SparkRichFormatter``, which allocates column widths against the current
    terminal width and collapses optional columns (path, function) before
    compressing the message column.

    When color is incompatible with the stream, the console is created without
    color and a one-time warning is emitted. When a pre-configured ``Console``
    is supplied directly, ``stream`` must not be set.

    Traceback rendering is controlled by ``traceback_policy``; Rich tracebacks
    are used only when ``exc_info`` survives the policy filter intact.
    """

    def __init__(
        self,
        level: int | str = NOTSET,
        console: "Console | None" = None,
        stream: SupportsWrite | None = None,
        *,
        # Main Settings
        use_color: bool = True,
        highlighter: Highlighter | None = None,
        traceback_policy: "TracebackOptions | None" = TracebackOptions.COMPACT,
        # Optional settings
        show_time: bool = True,
        show_level: bool = True,
        show_path: bool = True,
        show_function: bool = False,
        log_time_format: "str | FormatTimeCallable" = "%H:%M:%S",
        # Advanced settings
        settings: SparkRichHandlerSettings | None = None,
    ) -> None:
        """Set up Rich Console, apply color compatibility, and create the SparkRichFormatter."""

        if console is None:
            from rich.console import Console

            spark_stream = resolve_stream(stream)
            _compatible = is_color_compatible_terminal(spark_stream)
            # Rich Console requires IO[str]; SupportsWrite is structurally compatible
            rich_stream = cast(IO[str], spark_stream)
            # Force Behavior when color support is detected
            if _compatible:
                console = Console(
                    file=rich_stream,
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
                console = Console(file=rich_stream, tab_size=4, no_color=not use_color)
        else:
            if stream is not None:
                raise InvalidConfigurationError(
                    "Cannot set stream when passing in a pre-is_configured console."
                )

        if not is_color_compatible_terminal(cast(SupportsWrite, console.file)) and use_color:
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

        self._tb_policy = traceback_policy
        self._multiline = True
        self._warn_width_shown: bool = False
        self._spark_formatter: SparkRichFormatter = SparkRichFormatter(
            show_time=show_time,
            show_level=show_level,
            show_path=show_path,
            show_function=show_function,
            time_format=log_time_format,
            omit_repeated_times=settings.omit_repeated_times,
            level_width=settings.level_width,
            max_path_width=settings.max_path_width,
            max_function_width=settings.max_function_width,
            min_message_width=settings.min_message_width,
            indent_guide=settings.indent_guide,
        )

    def emit(self, record: LogRecord) -> None:
        """Apply traceback policy, render to a Rich renderable, and print via the console."""
        record = self.process_spark_log_record(record, self._multiline, self._tb_policy)
        message = self.format(record)

        if self._tb_policy == TracebackOptions.FULL and record.exc_info and record.exc_info != (None, None, None):
            traceback = self._apply_trace_formatting(record)
        elif getattr(record, "exc_text", None):
            traceback = record.exc_text
        else:
            traceback = None

        if traceback is not None:
            message = self._apply_time_formatting(record)

        message_renderable = self.render_message(record, message)

        log_renderable = self.render(
            record=record, traceback=traceback, message_renderable=message_renderable
        )
        if isinstance(self.console.file, NullFile):
            self.handleError(record)
        else:
            try:
                self.console.print(log_renderable)
            except Exception:
                self.handleError(record)

    def render(
        self,
        *,
        record: LogRecord,
        traceback: "Traceback | None | ConsoleRenderable",
        message_renderable: "ConsoleRenderable",
    ) -> "ConsoleRenderable":
        """Resolve path and time metadata from the record and delegate layout to ``SparkRichFormatter``."""
        # Resolve Path
        if isinstance(record, HasSparkAttributes):
            display_path = record.spark.filepath
            link_path = record.spark.uri
            lineno = record.spark.lineno
            func = record.spark.function
        else:
            display_path = Path(record.pathname)
            link_path = None
            lineno = record.lineno
            func = record.funcName

        # Resolve Renderables
        renderables = [message_renderable]
        if traceback:
            if isinstance(traceback, Traceback):
                renderables.append(Styled(traceback, Style(color="default", bold=False, dim=False)))
            else:
                renderables.append(Text(str(traceback), style=Style(color="default")))
        # Resolve Time
        time_format, log_time = self._resolve_time_format(record.created)

        log_renderable = self._spark_formatter(
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

        if self._spark_formatter.is_layout_degraded and not self._warn_width_shown:
            self._emit_degradation_warning()
        return log_renderable

    def _resolve_time_format(self, created: float) -> tuple[str | None, datetime]:
        """Return the active datefmt string and a datetime from the record's created timestamp."""
        if self.formatter is None:
            time_format = None
        else:
            time_format = self.formatter.datefmt
        return time_format, datetime.fromtimestamp(created)

    def _emit_degradation_warning(self) -> None:
        """Emit a one-time ``ConsoleWidthWarning`` listing which layout columns were hidden."""
        class ConsoleWidthWarning(UserWarning):
            """Warning emitted when found console size affects availability of layout elements"""

            pass

        cols = ", ".join(self._spark_formatter.degraded_columns())
        message = (
            "\nLogSpark layout degraded: \n"
            "  | terminal width ({width} cols) cannot satisfy the required message width ({message_width} cols)\n"
            "  | lower-priority metadata columns were hidden to preserve message readability: {cols}\n"
            "  | increase terminal width or reduce min_message_width to restore full layout."
        ).format(
            width=self.console.width, message_width=self._spark_formatter.min_message_width, cols=cols
        )
        emit_warning(
            message=message,
            category=ConsoleWidthWarning,
            stacklevel=4,
        )
        self._warn_width_shown = True

    def _apply_time_formatting(self, record: LogRecord) -> str:
        """Format the message string with asctime injection when a traceback replaces the main body."""
        message = record.getMessage()
        if self.formatter:
            record.message = record.getMessage()
            formatter = self.formatter
            if hasattr(formatter, "usesTime") and formatter.usesTime():
                record.asctime = formatter.formatTime(record, formatter.datefmt)
            message = formatter.formatMessage(record)
        return message

    def _apply_trace_formatting(self, record: LogRecord) -> "Traceback":
        """Build a Rich ``Traceback`` renderable from the record's exc_info."""
        assert record.exc_info is not None
        exc_type, exc_value, exc_traceback = record.exc_info
        assert exc_type is not None
        assert exc_value is not None
        traceback = Traceback.from_exception(
            exc_type,
            exc_value,
            exc_traceback,
            width=self.tracebacks_width,
            code_width=self.tracebacks_code_width,
            extra_lines=self.tracebacks_extra_lines,
            theme=self.tracebacks_theme,
            word_wrap=self.tracebacks_word_wrap,
            show_locals=self.tracebacks_show_locals,
            locals_max_length=self.locals_max_length,
            locals_max_string=self.locals_max_string,
            suppress=self.tracebacks_suppress,
            max_frames=self.tracebacks_max_frames,
        )

        return traceback
