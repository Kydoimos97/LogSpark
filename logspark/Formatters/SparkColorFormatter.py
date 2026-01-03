import logging


class SparkColorFormatter(logging.Formatter):
    LEVEL_COLORS = {
        logging.DEBUG: "\033[90m",  # gray
        logging.WARNING: "\033[33m",  # yellow
        logging.ERROR: "\033[31m",  # red
        logging.CRITICAL: "\033[35m",  # magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        color = self.LEVEL_COLORS.get(record.levelno)
        if not color:
            return msg  # INFO (and others) remain unstyled
        return f"{color}{msg}{self.RESET}"
