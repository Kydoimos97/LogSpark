import logging
from typing import Mapping, Literal, Any

from pythonjsonlogger.json import JsonFormatter
from ..Formatters.SparkBaseFormatter import SparkBaseFormatter
from ..Types.Options import TracebackOptions


class SparkJsonFormatter(SparkBaseFormatter):
    """
    Wrapper formatter that enforces single-line JSON output invariant

    This formatter wraps python-json-logger to ensure all output is single-line,
    including traceback information, regardless of traceback policy.

    Invariant:
        Each emitted log record results in exactly one line of JSON output.


    """

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        style: Literal["%", "{", "$"] = "%",
        validate: bool = True,
        *,
        defaults: Mapping[str, Any] | None = None,
        tb_policy: TracebackOptions | None = None,
        **kwargs,
    ):
        super().__init__(
            fmt, datefmt, style, validate, defaults=defaults, tb_policy=tb_policy, multiline=False
        )
        self._json_formatter = JsonFormatter(
            fmt=fmt, datefmt=datefmt, style=style, validate=validate, defaults=defaults, **kwargs
        )

    def format(self, record: logging.LogRecord) -> str:
        """
        Format record ensuring single-line JSON output.
        """
        record = self.process_spark_log_record(record, self._multiline, self._tb_policy)
        # jsonformatter checks:
        # if record.exc_info and not message_dict['exc_info']
        # if not message_dict['exc_info'] and record.exc_text <- targeted so setting exc info to None
        formatted: str = self._json_formatter.format(record)

        # Physical single-line invariant only (JSON-safe)
        return formatted.replace("\n", " ").replace("\r", " ").strip()
