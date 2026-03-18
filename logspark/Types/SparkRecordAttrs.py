from __future__ import annotations

from dataclasses import dataclass
from logging import LogRecord
from pathlib import Path
from traceback import FrameSummary, StackSummary, extract_tb
from types import TracebackType
from typing import Protocol, Literal, TypeGuard, runtime_checkable


@dataclass(slots=True)
class SparkRecordAttrs:
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
        return self.exc_type.__name__

    @property
    def name(self) -> str:
        return self.function

    @classmethod
    def from_record(cls, record: LogRecord) -> SparkRecordAttrs:
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

        # Extract exception info
        exc_type: type[BaseException] | None = record.exc_info[0]
        exc_value: BaseException | None = record.exc_info[1]
        tb: TracebackType | None = record.exc_info[2]
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
    spark: SparkRecordAttrs


@runtime_checkable
class ExceptionOriginEnabled(HasSparkAttributes, Protocol):
    """Enabled using the factory function"""
    _spark_exc: Literal[True]


def is_spark_exception_enabled(record: LogRecord) -> TypeGuard[ExceptionOriginEnabled | LogRecord]:
    return getattr(record, "_spark_exc", False) is True


def has_spark_extra_attributes(record: LogRecord) -> TypeGuard[HasSparkAttributes | LogRecord]:
    return (hasattr(record, "spark")
            and record.spark is not None # noqa
            and isinstance(record.spark, SparkRecordAttrs))

