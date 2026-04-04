from __future__ import annotations

from dataclasses import dataclass
from logging import LogRecord
from pathlib import Path
from traceback import FrameSummary, StackSummary, extract_tb
from types import TracebackType
from typing import Literal, Protocol, TypeGuard, runtime_checkable


@dataclass(slots=True)
class SparkRecordAttrs:
    """
    Structured metadata extracted from a ``logging.LogRecord`` for use by LogSpark formatters.

    Populated by ``TracebackPolicyFilter`` and ``PathNormalizationFilter`` at filter
    time. Formatters read from this dataclass rather than from raw record attributes,
    allowing path resolution and exception origin to be applied consistently regardless
    of which formatter is active.

    ``from_record()`` is the primary constructor; direct instantiation is for tests only.
    """
    filename: str
    filepath: Path
    lineno: int | None
    function: str | None
    uri: str | None

    exc_type: type[BaseException] | None
    exc_value: BaseException | None
    exc_traceback: TracebackType | None = None

    @property
    def is_exception(self) -> bool:
        return self.exc_type is not None and self.exc_value is not None

    @property
    def exc_name(self) -> str:
        return self.exc_type.__name__ if self.exc_type is not None else "UnknownError"

    @property
    def name(self) -> str | None:
        return self.function

    @classmethod
    def from_record(cls, record: LogRecord) -> SparkRecordAttrs:
        """Construct a ``SparkRecordAttrs`` from a ``LogRecord``, extracting the last traceback frame when available."""
        exc_info = getattr(record, "exc_info", None)

        if exc_info is None or exc_info == (None, None, None):
            instance = cls(
                filename=record.filename,
                filepath=Path(record.pathname),
                lineno=record.lineno,
                function=record.funcName,
                uri = None,
                exc_type=None,
                exc_value=None,
                exc_traceback=None,
            )
            return instance

        # Extract exception info (use local exc_info which is Any from getattr, not the
        # typed record.exc_info attribute which includes None in its union)
        exc_type: type[BaseException] | None = exc_info[0]
        exc_value: BaseException | None = exc_info[1]
        tb: TracebackType | None = exc_info[2]
        if tb is None:
            # Some cases where exc_info is set but no traceback is available
            instance = cls(
                filename=record.filename,
                filepath=Path(record.pathname),
                lineno=record.lineno,
                function=record.funcName,
                uri=None,
                exc_type=exc_type,
                exc_value=exc_value,
                exc_traceback=None,
            )
            return instance

        # Extract last frame from traceback
        tb_frames: list[FrameSummary] | StackSummary = extract_tb(tb)
        last_frame: FrameSummary = tb_frames[-1]
        instance = cls(
            filename=last_frame.filename,
            filepath=Path(last_frame.filename),
            lineno=last_frame.lineno,
            function=last_frame.name,
            uri=None,
            exc_type=exc_type,
            exc_value=exc_value,
            exc_traceback=tb,
        )
        return instance


@runtime_checkable
class HasSparkAttributes(Protocol):
    """Runtime-checkable protocol for records that carry a ``SparkRecordAttrs`` instance."""

    spark: SparkRecordAttrs


@runtime_checkable
class ExceptionOriginEnabled(HasSparkAttributes, Protocol):
    """Protocol for records that have both ``SparkRecordAttrs`` and the traceback policy flag set."""

    _spark_exc: Literal[True]


def is_spark_exception_enabled(record: object) -> TypeGuard[ExceptionOriginEnabled]:
    """Return True when the record has the traceback policy flag (``_spark_exc == True``) set."""
    return getattr(record, "_spark_exc", False) is True


def has_spark_extra_attributes(record: object) -> TypeGuard[HasSparkAttributes]:
    """Return True when the record has a ``spark`` attribute that is a ``SparkRecordAttrs`` instance."""
    spark = getattr(record, "spark", None)
    return spark is not None and isinstance(spark, SparkRecordAttrs)

