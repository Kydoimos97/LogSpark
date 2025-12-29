import logging
import sys
import traceback
from types import TracebackType
from typing import Optional, TYPE_CHECKING

from ..Internal.State import is_silenced_mode
from ..Internal.Func import get_devnull
from ..Types import MissingDependencyException
from ..Types.Protocol import SupportsWrite
from ..Types import TracebackOptions

if TYPE_CHECKING:
    from pythonjsonlogger.json import JsonFormatter


class _SingleLineJSONFormatter(logging.Formatter):
    """
    Wrapper formatter that enforces single-line JSON output invariant

    This formatter wraps python-json-logger to ensure all output is single-line,
    including traceback information, regardless of traceback policy.
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
        Format record ensuring single-line output

        Args:
            record: LogRecord to format

        Returns:
            Single-line JSON string
        """
        # Handle traceback information if present
        if record.exc_info:
            # Format traceback according to policy stored in record
            exc_type: Optional[type[BaseException]] = record.exc_info[0]
            exc_value: Optional[BaseException] = record.exc_info[1]
            tb: Optional[TracebackType] = record.exc_info[2]
            traceback_policy = getattr(record, "traceback_policy", TracebackOptions.NONE)

            if traceback_policy == TracebackOptions.NONE or exc_type is None or exc_value is None:
                # Remove exception info to prevent traceback inclusion
                record.exc_info = None
                record.exc_text = None
            elif traceback_policy == TracebackOptions.COMPACT:
                # Format compact traceback as single line - essential info only
                try:
                    # Get the most relevant frame (usually the last one)
                    tb_frames = traceback.extract_tb(tb)
                    if tb_frames:
                        last_frame = tb_frames[-1]
                        compact_tb = (
                            f"{exc_type.__name__}: {exc_value} | "
                            f"{last_frame.filename}:{last_frame.lineno} "
                            f"in {last_frame.name}"
                        )
                    else:
                        compact_tb = f"{exc_type.__name__}: {exc_value}"

                    # Set exc_text which python-json-logger will use as exc_info field
                    record.exc_text = compact_tb
                except Exception:
                    # Fallback if traceback processing fails
                    record.exc_text = f"{exc_type.__name__}: {exc_value}"

                record.exc_info = None  # Prevent default formatting

            elif traceback_policy == TracebackOptions.FULL:
                # Format full traceback as single line - complete info but single line
                try:
                    exc_lines = traceback.format_exception(exc_type, exc_value, tb)
                    # Join all lines and convert to single line by replacing newlines with ' | '
                    full_tb = "".join(exc_lines).replace("\n", " | ").replace("\r", "").strip()
                    record.exc_text = full_tb
                except Exception:
                    # Fallback if traceback processing fails
                    record.exc_text = f"{exc_type.__name__}: {exc_value}"

                record.exc_info = None  # Prevent default formatting

        # Format using python-json-logger
        formatted: str = self._json_formatter.format(record)

        # Critical invariant: Ensure single-line output by replacing any remaining newlines
        # This is the final enforcement point for the single-line JSON invariant
        single_line = formatted.replace("\n", " | ").replace("\r", "").strip()

        return single_line


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

    def __init__(self, stream: Optional[SupportsWrite] = None):
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

        except ImportError:
            raise MissingDependencyException(["python-json-logger"])
