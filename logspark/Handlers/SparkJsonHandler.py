import logging
import sys

from ..Formatters import SparkJsonFormatter
from ..Types import MissingDependencyException
from ..Types.Protocol import SupportsWrite
from .._Internal.Func import get_devnull
from .._Internal.State import is_silenced_mode


class SparkJsonHandler(logging.StreamHandler[SupportsWrite]):
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
        from logspark.handlers import SparkJsonHandler

        logger.configure(
            level=logging.INFO,
            handler=SparkJsonHandler()
        )

        logger.info("User action", extra={
            "user_id": 123,
            "action": "login",
            "ip_address": "192.168.1.1"
        })
        # Output: {"timestamp": "2023-...", "level": "INFO", "message": "User action", "user_id": 123, ...}
        ```
    """

    def __init__(self, stream: SupportsWrite | None = None) -> None:
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
            self.setFormatter(SparkJsonFormatter(formatter))

        except ImportError as e:
            raise MissingDependencyException(["python-json-logger"]) from e