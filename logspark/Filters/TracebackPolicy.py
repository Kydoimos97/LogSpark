import logging
from dataclasses import dataclass
from pathlib import Path
from traceback import FrameSummary, StackSummary, extract_tb, format_exception
from types import TracebackType
from typing import Any, Protocol, runtime_checkable

from .._Internal import SparkFilterModule
from ..Types.Options import TracebackOptions


@dataclass(slots=True, frozen=True)
class ExceptionOrigin:
    filename: str
    filepath: Path
    lineno: int | None
    function: str | None
    policy: TracebackOptions | None = None

    @classmethod
    def from_frame(cls, frame: FrameSummary, policy: TracebackOptions) -> "ExceptionOrigin":
        return cls(frame.filename, Path(frame.filename), frame.lineno, frame.name, policy)


@runtime_checkable
class SupportsExceptionOrigin(Protocol):
    exc_origin: ExceptionOrigin


class TracebackPolicy(SparkFilterModule):
    traceback_policy: TracebackOptions
    single_line_mode: bool

    def configure(
        self,
        *,
        traceback_policy: TracebackOptions | None = None,
        single_line_mode: bool | None = None,
            **kwargs: Any,
    ) -> None:
        if traceback_policy is not None:
            self.traceback_policy = traceback_policy
        if single_line_mode is not None:
            self.single_line_mode = single_line_mode

    def _ext_init(self) -> None:
        self.traceback_policy = TracebackOptions.COMPACT
        self.single_line_mode = False

    def filter(self, record: logging.LogRecord) -> bool:
        if not record.exc_info:
            return True
        else:
            exc_type: type[BaseException] | None = record.exc_info[0]
            exc_value: BaseException | None = record.exc_info[1]
            tb: TracebackType | None = record.exc_info[2]
            last_frame: FrameSummary | None = None
        if tb is not None:
            tb_frames: list[FrameSummary] | StackSummary = extract_tb(tb)
            last_frame = tb_frames[-1]
            record.exc_origin = ExceptionOrigin.from_frame(
                frame=last_frame, policy=self.traceback_policy
            )

            # its a feature of this traceback policy to point to error origins not error caller
            # If you don't use downstream spark classes injection ensures stdlib
            # compatible code take into account error site not call site.
            if self._inject and isinstance(record, SupportsExceptionOrigin):
                record.pathname = record.exc_origin.filename
                record.lineno = record.exc_origin.lineno
                record.funcName = record.exc_origin.function
        if exc_type is None or exc_value is None:
            record.exc_info = None
            record.exc_text = None
        elif not self.single_line_mode:
            self._prepare_standard_record(
                record=record, exc_type=exc_type, exc_value=exc_value, last_frame=last_frame
            )
        else:
            self._prepare_single_line_record(
                record=record, exc_type=exc_type, exc_value=exc_value, last_frame=last_frame, tb=tb
            )

        return True

    def _prepare_standard_record(
        self,
        record: logging.LogRecord,
        exc_type: type[BaseException],
        exc_value: BaseException,
        last_frame: FrameSummary | None,
    ) -> None:
        if self.traceback_policy == TracebackOptions.HIDE or last_frame is None:
            # Hide the traceback not the log
            record.exc_info = None
            record.exc_text = f"{exc_type.__name__}: {exc_value}"
        elif self.traceback_policy == TracebackOptions.COMPACT:
            # Format compact traceback for terminal display
            try:
                compact_tb = (
                    f"{exc_type.__name__}: {exc_value}\n  "
                    f'    At "{last_frame.filename}:{last_frame.lineno}", '
                )

                if last_frame.name:
                    compact_tb += f", in {last_frame.name}"
                record.exc_text = compact_tb
            except Exception:
                # Fallback if traceback processing fails
                record.exc_text = f"{exc_type.__name__}: {exc_value}"

            record.exc_info = None  # Prevent default Rich traceback formatting
        else:
            # no special formatting required
            pass

    def _prepare_single_line_record(
        self,
        record: logging.LogRecord,
        exc_type: type[BaseException],
        exc_value: BaseException,
        last_frame: FrameSummary | None,
        tb: TracebackType | None,
    ) -> None:
        record.exc_info = None  # remove exc info as we want to handle all of it
        if self.traceback_policy == TracebackOptions.HIDE or last_frame is None:
            # Hide the traceback not the log
            record.exc_text = f"{exc_type.__name__}: {self._sanitize(exc_value)}"
        elif self.traceback_policy == TracebackOptions.COMPACT:
            try:
                if last_frame is not None:
                    record.exc_text = (
                        f"{exc_type.__name__}: {self._sanitize(exc_value)} | "
                        f"{last_frame.filename}:{last_frame.lineno} in {last_frame.name}"
                    )
                else:
                    record.exc_text = f"{exc_type.__name__}: {self._sanitize(exc_value)}"
            except Exception:
                record.exc_text = f"{exc_type.__name__}: {self._sanitize(exc_value)}"
        elif self.traceback_policy == TracebackOptions.FULL:
            try:
                if tb is not None:
                    lines = format_exception(exc_type, exc_value, tb)
                    record.exc_text = " | ".join(
                        self._sanitize(line) for line in lines if line.strip()
                    )
                else:
                    record.exc_text = f"{exc_type.__name__}: {self._sanitize(exc_value)}"
            except Exception:
                record.exc_text = f"{exc_type.__name__}: {self._sanitize(exc_value)}"

    @staticmethod
    def _sanitize(value: object) -> str:
        return str(value).replace("\n", " ").replace("\r", " ").strip()
