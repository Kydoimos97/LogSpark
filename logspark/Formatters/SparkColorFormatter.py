import logging

from ..Formatters.SparkBaseFormatter import SparkBaseFormatter


class SparkColorFormatter(SparkBaseFormatter):
    """
    ANSI-color-aware formatter for terminals that support 256-color or truecolor output.

    Wraps ``SparkBaseFormatter`` with level-based ANSI color codes. DEBUG is
    rendered in gray, WARNING in yellow, ERROR in red, CRITICAL in magenta;
    INFO and other levels remain unstyled. Used by ``SparkTerminalHandler``
    when ``is_color_compatible_terminal()`` returns True.
    """

    LEVEL_COLORS = {
        logging.DEBUG: "\033[90m",  # gray
        logging.WARNING: "\033[33m",  # yellow
        logging.ERROR: "\033[31m",  # red
        logging.CRITICAL: "\033[35m",  # magenta
    }
    RESET = "\033[0m"


    def format(self, record: logging.LogRecord) -> str:
        """Format via SparkBaseFormatter then wrap the result in the appropriate ANSI color code."""
        msg = super().format(record)
        color = self.LEVEL_COLORS.get(record.levelno)
        if not color:
            return msg  # INFO (and others) remain unstyled
        return f"{color}{msg}{self.RESET}"
