import logging
import sys
import traceback
from types import TracebackType
from typing import TYPE_CHECKING

from .._Internal.Func import get_devnull
from .._Internal.State import is_silenced_mode
from ..Types import MissingDependencyException, TracebackOptions
from ..Types.Protocol import SupportsWrite

if TYPE_CHECKING:
    from pythonjsonlogger.json import JsonFormatter


class _SingleLineJSONFormatter(logging.Formatter):
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


class JSONHandler(logging.StreamHandler[SupportsWrite]):
    """
    JSON structured logging handler using python-json-logger backend.

    Produces single-line JSON output suitable for log aggregation systems,
    structured logging pipelines, and production environments. Each log
    record is formatted as a complete JSON object on a single line.

    Features:
    - Structured JSON output with consistent schema
    - Automatic field extraction from LogRecord attributes
    - Support for extra fields via the 'extra' parameter
    - Single-line output invariant for easy parsing
    - Traceback policy integration for error handling

    Example:
        ```python
        from logspark import logger
        from logspark.handlers import JSONHandler

        logger.configure(
            level=logging.INFO,
            handler=JSONHandler()
        )

        logger.info("User action", extra={
            "user_id": 123,
            "action": "login",
            "ip_address": "192.168.1.1"
        })
        # Output: {"timestamp": "2023-...", "level": "INFO", "message": "User action", "user_id": 123, ...}
        ```
    """

    def __init__(self, stream: SupportsWrite | None = None):
        """
        Initialize JSON handler with python-json-logger backend.

        Args:
            stream: Output stream for JSON log records. If None, defaults to sys.stdout.
                   Can be any object that supports write() method (file, StringIO, etc.).

        Raises:
            MissingDependencyException: If python-json-logger is not installed.

        Note:
            The handler automatically configures structured JSON formatting with
            standard fields including timestamp, level, message, and source location.
            Additional fields can be added via the 'extra' parameter in log calls.
        """

        if is_silenced_mode():
            stream = get_devnull()
        else:
            stream = stream or sys.stdout

        super().__init__(stream or sys.stdout)

        # Import and configure python-json-logger backend
        try:
            # Create formatter that produces structured JSON output
            # Include standard fields and any extra fields from LogRecord
            from pythonjsonlogger.json import JsonFormatter

            formatter = JsonFormatter(
                fmt=(
                    "%(name)s "
                    "%(asctime)s "
                    "%(levelname)-8s "
                    "%(message)s"
                    "%(filename)s:%(lineno)d "
                    "%(funcName)s "
                ),
                datefmt="%Y-%m-%d %H:%M:%S",
            )

            # Wrap formatter to ensure single-line output and handle tracebacks
            self.setFormatter(_SingleLineJSONFormatter(formatter))

        except ImportError as e:
            raise MissingDependencyException(["python-json-logger"]) from e
