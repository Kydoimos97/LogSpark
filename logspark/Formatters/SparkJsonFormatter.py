import logging
import traceback
from types import TracebackType

from pythonjsonlogger.json import JsonFormatter

from ..Types import TracebackOptions


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
        if record.exc_info:
            self._apply_traceback_policy(record)

        formatted: str = self._json_formatter.format(record)

        # Physical single-line invariant only (JSON-safe)
        return formatted.replace("\n", " ").replace("\r", " ").strip()

    def _apply_traceback_policy(self, record: logging.LogRecord) -> None:
        exc_info = record.exc_info
        assert exc_info is not None

        exc_type: type[BaseException] | None = exc_info[0]
        exc_value: BaseException | None = exc_info[1]
        tb: TracebackType | None = exc_info[2]
        policy: TracebackOptions = getattr(record, "traceback_policy", TracebackOptions.COMPACT)

        if not exc_type or not exc_value or policy == TracebackOptions.NONE:
            self._clear_exception(record)
            return

        if policy == TracebackOptions.COMPACT:
            record.exc_text = self._format_compact(exc_type, exc_value, tb)
        elif policy == TracebackOptions.FULL:
            record.exc_text = self._format_full(exc_type, exc_value, tb)

        record.exc_info = None

    @staticmethod
    def _clear_exception(record: logging.LogRecord) -> None:
        record.exc_info = None
        record.exc_text = None

    def _format_compact(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        tb: TracebackType | None,
    ) -> str:
        """
        Format exception using COMPACT traceback policy.
        Expected shape:
        "<ExceptionType>: <message> | <filename>:<lineno> in <function>"
        """
        try:
            if tb is None:
                return f"{exc_type.__name__}: {self._sanitize(exc_value)}"
            frames = traceback.extract_tb(tb)
            if frames:
                frame = frames[-1]
                return (
                    f"{exc_type.__name__}: {self._sanitize(exc_value)} | "
                    f"{frame.filename}:{frame.lineno} in {frame.name}"
                )
            return f"{exc_type.__name__}: {self._sanitize(exc_value)}"
        except Exception:
            return f"{exc_type.__name__}: {self._sanitize(exc_value)}"

    def _format_full(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        tb: TracebackType | None,
    ) -> str:
        """
        Format exception using FULL traceback policy.
        Expected shape (single line):
        "Traceback (most recent call last): | File \"...\", line X, in func | ... | ValueError: message"
        """
        try:
            if tb is None:
                return f"{exc_type.__name__}: {self._sanitize(exc_value)}"
            lines = traceback.format_exception(exc_type, exc_value, tb)
            return " | ".join(self._sanitize(line) for line in lines if line.strip())
        except Exception:
            return f"{exc_type.__name__}: {self._sanitize(exc_value)}"

    @staticmethod
    def _sanitize(value: object) -> str:
        return str(value).replace("\n", " ").replace("\r", " ").strip()
