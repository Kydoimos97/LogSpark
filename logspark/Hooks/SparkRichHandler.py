#  Copyright (c) 2025.
#  Author: Willem van der Schans.
#  Licensed under the MIT License (https://opensource.org/license/mit).
import logging
import os
from datetime import datetime
from pathlib import Path

from rich._log_render import FormatTimeCallable
from rich.console import Console, ConsoleRenderable
from rich.highlighter import Highlighter
from rich.logging import RichHandler
from rich.traceback import Traceback

from .CustomLogRender import CustomLogRender

PYTHONPATH = os.environ.get("PYTHONPATH", None)
PYTHONPATH = PYTHONPATH.split(";")[0] if PYTHONPATH else None


class SparkRichHandler(RichHandler):
    def __init__(
        self,
        level: int | str = logging.NOTSET,
        console: Console | None = None,
        *,
        show_time: bool = True,
        show_level: bool = True,
        show_path: bool = True,
        show_function: bool = False,
        markup: bool = False,
        rich_tracebacks: bool = False,
        tracebacks_width: int | None = None,
        tracebacks_extra_lines: int = 3,
        tracebacks_theme: str | None = None,
        tracebacks_word_wrap: bool = True,
        tracebacks_show_locals: bool = False,
        log_time_format: str | FormatTimeCallable = "%H:%M:%S",
        highlighter: Highlighter | None = None,
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
            tracebacks_theme=tracebacks_theme,
            tracebacks_word_wrap=tracebacks_word_wrap,
            tracebacks_show_locals=tracebacks_show_locals,
            log_time_format=log_time_format,
            highlighter=highlighter,
        )
        self._c_log_render: CustomLogRender = CustomLogRender(
            show_time=show_time,
            show_level=show_level,
            show_path=show_path,
            show_function=show_function,
            time_format=log_time_format,
            omit_repeated_times=True,
            level_width=8,
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

        return log_renderable
