import logging
import sys

from .._Internal.Func import get_devnull
from .._Internal.State import is_silenced_mode
from ..Formatters import SparkJsonFormatter
from ..Types import MissingDependencyException
from ..Types.Protocol import SupportsWrite


class SparkJsonHandler(logging.StreamHandler[SupportsWrite]):
    """
    Structured JSON logging handler backed by python-json-logger.

    Emits one JSON object per log record on a single line, making output
    suitable for log aggregation pipelines and production environments.
    Extra fields passed via ``extra=`` in log calls are included in the
    JSON object automatically.

    Requires python-json-logger; raises ``MissingDependencyException`` at
    construction time if the package is absent.
    """

    def __init__(self, stream: SupportsWrite | None = None) -> None:
        """Initialize the handler with ``SparkJsonFormatter``; raises ``MissingDependencyException`` if python-json-logger is absent."""

        resolved: SupportsWrite
        if is_silenced_mode():
            resolved = get_devnull()
        else:
            resolved = stream if stream is not None else sys.stdout

        super().__init__(resolved)

        # Import and configure python-json-logger backend
        try:
            self.setFormatter(SparkJsonFormatter(
                fmt=(
                    "%(name)s "
                    "%(asctime)s "
                    "%(levelname)-8s "
                    "%(message)s"
                    "%(filename)s:%(lineno)d "
                    "%(funcName)s "
                ),
                datefmt="%Y-%m-%d %H:%M:%S",
            ))

        except ImportError as e:
            raise MissingDependencyException(["python-json-logger"]) from e
