import logging

from ..Formatters.SparkBaseFormatter import SparkBaseFormatter


class SparkColorFormatter(SparkBaseFormatter):
    LEVEL_COLORS = {
        logging.DEBUG: "\033[90m",  # gray
        logging.WARNING: "\033[33m",  # yellow
        logging.ERROR: "\033[31m",  # red
        logging.CRITICAL: "\033[35m",  # magenta
    }
    RESET = "\033[0m"


    def format(self, record: logging.LogRecord) -> str:
        # Base exc formatting checks:
        # if record.exc_info:
        # if not record.exc_text:
        # record.exc_text = self.formatException(record.exc_info)
        record = self.process_spark_log_record(record, self._multiline, self._tb_policy)
        msg = super().format(record)
        color = self.LEVEL_COLORS.get(record.levelno)
        if not color:
            return msg  # INFO (and others) remain unstyled
        return f"{color}{msg}{self.RESET}"
