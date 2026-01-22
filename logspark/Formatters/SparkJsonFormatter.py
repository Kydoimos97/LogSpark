import logging

from pythonjsonlogger.json import JsonFormatter


class SparkJsonFormatter(logging.Formatter):
    """
    Wrapper formatter that enforces single-line JSON output invariant

    This formatter wraps python-json-logger to ensure all output is single-line,
    including traceback information, regardless of traceback policy.

    Record mutation:
        This handler may mutate ``LogRecord.exc_info`` and ``LogRecord.exc_text``
        during formatting in order to enforce traceback policy and the
        single-line JSON invariant. These mutations are confined to the
        formatting phase and do not affect upstream logging behavior.

    Invariant:
        Each emitted log record results in exactly one line of JSON output.


    """

    def __init__(self, json_formatter: "JsonFormatter") -> None:
        """
        Initialize wrapper formatter

        Args:
            json_formatter: python-json-logger JsonFormatter instance
        """
        super().__init__()
        self._json_formatter = json_formatter

    def format(self, record: logging.LogRecord) -> str:
        """
        Format record ensuring single-line JSON output.
        """
        formatted: str = self._json_formatter.format(record)

        # Physical single-line invariant only (JSON-safe)
        return formatted.replace("\n", " ").replace("\r", " ").strip()
