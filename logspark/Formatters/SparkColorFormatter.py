import logging
from typing import TYPE_CHECKING

from ..Formatters.SparkBaseFormatter import SparkBaseFormatter
from ..Types.SparkRecordAttrs import has_spark_extra_attributes

if TYPE_CHECKING:
    from ..Types.Options import TracebackOptions


class SparkColorFormatter(SparkBaseFormatter):
    """
    Per-segment ANSI-color formatter for color-capable terminals.

    Replaces whole-line coloring with per-field styling: timestamps and paths
    are dimmed, the level badge carries a level-specific color, and the message
    inherits the level color. INFO remains unstyled for visual contrast.

    When ``link_path=True`` and the record carries a ``spark.uri``, the path
    segment is wrapped in an OSC 8 terminal hyperlink so terminals that support
    it (iTerm2, WezTerm, VS Code, Windows Terminal) open the file on click.
    """

    _GRAY = "\033[90m"
    _RESET = "\033[0m"

    _BADGE_COLORS = {
        logging.DEBUG:    "\033[36m",    # cyan
        logging.INFO:     "\033[32m",    # green
        logging.WARNING:  "\033[33m",    # yellow
        logging.ERROR:    "\033[31m",    # red
        logging.CRITICAL: "\033[1;35m",  # bold magenta
    }

    _MSG_COLORS = {
        logging.DEBUG:    "\033[90m",    # gray
        logging.WARNING:  "\033[33m",    # yellow
        logging.ERROR:    "\033[31m",    # red
        logging.CRITICAL: "\033[35m",    # magenta
        # INFO intentionally absent — rendered unstyled for contrast
    }

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        *,
        show_time: bool = True,
        show_level: bool = True,
        show_path: bool = True,
        show_function: bool = False,
        level_width: int = 9,
        link_path: bool = False,
        tb_policy: "TracebackOptions | None" = None,
        multiline: bool = True,
    ) -> None:
        """Initialize field visibility, level width, OSC 8 toggle, and traceback policy."""
        super().__init__(fmt=fmt, datefmt=datefmt, tb_policy=tb_policy, multiline=multiline)
        self._show_time = show_time
        self._show_level = show_level
        self._show_path = show_path
        self._show_function = show_function
        self._level_width = level_width
        self._link_path = link_path

    def format(self, record: logging.LogRecord) -> str:
        """Render each log field with independent ANSI styling and assemble the final line."""
        record = self.process_spark_log_record(record, self._multiline, self._tb_policy)

        badge_color = self._BADGE_COLORS.get(record.levelno, "")
        msg_color = self._MSG_COLORS.get(record.levelno, "")

        parts: list[str] = []

        if self._show_time:
            asctime = self.formatTime(record, self.datefmt)
            parts.append(f"{self._GRAY}{asctime}{self._RESET}")

        if self._show_level:
            level_str = f"{record.levelname:<{self._level_width}}"
            parts.append(f"{badge_color}{level_str}{self._RESET}")

        if self._show_path:
            parts.append(self._render_path(record))

        if self._show_function:
            parts.append(f"{self._GRAY}{record.funcName}{self._RESET}")

        message = record.getMessage()
        msg_part = f"{msg_color}{message}{self._RESET}" if msg_color else message

        line = " - ".join(parts)
        line += f" -> {msg_part}" if parts else msg_part

        exc_text = getattr(record, "exc_text", None)
        if exc_text:
            line += f"\n{self._GRAY}{exc_text}{self._RESET}"

        return line

    def _render_path(self, record: logging.LogRecord) -> str:
        """Return the dimmed path:lineno segment, with an OSC 8 hyperlink when enabled."""
        if has_spark_extra_attributes(record):
            spark = record.spark
            path_str = spark.filepath.as_posix()
            lineno = spark.lineno
            uri = spark.uri if self._link_path else None
        else:
            path_str = record.filename
            lineno = record.lineno
            uri = None

        display = f"{path_str}:{lineno}"

        if uri:
            display = f"\x1b]8;;{uri}\x1b\\{display}\x1b]8;;\x1b\\"

        return f"{self._GRAY}{display}{self._RESET}"
