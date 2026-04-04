import logging
from traceback import format_exception
from typing import Any, Literal, Mapping, cast

from ..Types.Options import TracebackOptions
from ..Types.SparkRecordAttrs import (
    SparkRecordAttrs,
    has_spark_extra_attributes,
    is_spark_exception_enabled,
)


class SparkBaseFormatMixin:
    """
    Mixin that applies the LogSpark traceback policy to a log record before formatting.

    Shared between ``SparkBaseFormatter`` (stdlib path) and ``SparkRichHandler``
    (Rich path). Call ``process_spark_log_record()`` before invoking the formatter;
    it rewrites ``record.exc_text`` according to the active policy and clears
    ``record.exc_info`` so the base formatter does not re-render the traceback.
    Errors raised inside this method are swallowed silently to keep logging robust.
    """

    @classmethod
    def process_spark_log_record(cls, record: logging.LogRecord, multiline: bool = True, traceback_policy: TracebackOptions | None = None):
        """Apply the traceback policy to exc_text and optionally collapse the record to a single line."""
        try:
            if is_spark_exception_enabled(record) and has_spark_extra_attributes(record):
                if record.spark.is_exception:
                    if multiline:
                        exc_text = cls._get_multiline_tb(record.spark, traceback_policy)
                    else:
                        exc_text = cls._get_single_line_tb(record.spark, traceback_policy)
                    _r = cast(logging.LogRecord, record)
                    _r.exc_text = exc_text
                    _r.exc_info = None
        except Exception:
            pass

        if not multiline:
            record = cls._collapse_to_single_line(record)

        return record

    @staticmethod
    def _get_multiline_tb(
        spark_attrs: SparkRecordAttrs,
        traceback_policy: TracebackOptions | None,
    ) -> str | None:
        """Render the traceback as a multiline string according to the given policy."""

        exc_text = None
        if traceback_policy == TracebackOptions.HIDE:
            exc_text = f"{spark_attrs.exc_name}: {spark_attrs.exc_value}"
        elif traceback_policy == TracebackOptions.COMPACT:
            try:
                compact_tb = (
                    f'{spark_attrs.exc_name}: {spark_attrs.exc_value}\n      At "{spark_attrs.filename}:{spark_attrs.lineno}"'
                )
                if spark_attrs.name:
                    compact_tb += f", in {spark_attrs.name}"
                exc_text = compact_tb
            except Exception:
                exc_text = f"{spark_attrs.exc_name}: {spark_attrs.exc_value}"
        elif traceback_policy == TracebackOptions.FULL and spark_attrs.exc_traceback is not None:
            try:
                exc_text = "".join(
                    format_exception(spark_attrs.exc_type, spark_attrs.exc_value, spark_attrs.exc_traceback)
                ).rstrip()
            except Exception:
                exc_text = f"{spark_attrs.exc_name}: {spark_attrs.exc_value}"

        return exc_text

    @staticmethod
    def _get_single_line_tb(
            spark_attrs: SparkRecordAttrs, traceback_policy: TracebackOptions | None,
    ) -> str | None:
        """Render the traceback as a single-line string with newlines replaced by spaces."""

        def _sanitize(value: object) -> str:
            return str(value).replace("\n", " ").replace("\r", " ").strip()

        default_text = f"{spark_attrs.exc_name}: {_sanitize(spark_attrs.exc_value)} | {spark_attrs.filename}:{spark_attrs.lineno} in {spark_attrs.name}"
        exc_text: str | None = default_text

        if traceback_policy == TracebackOptions.HIDE or not spark_attrs.is_exception:
            exc_text = f"{spark_attrs.exc_name}: {_sanitize(spark_attrs.exc_value)}"
        elif traceback_policy == TracebackOptions.FULL and spark_attrs.exc_traceback is not None:
            try:
                exc_text = "\n".join(format_exception(spark_attrs.exc_type, spark_attrs.exc_value, spark_attrs.exc_traceback))
            except Exception:
                pass  # exc_text remains default_text

        return exc_text

    @staticmethod
    def _collapse_to_single_line(record: logging.LogRecord) -> logging.LogRecord:
        """Flatten all newlines in exc_text and message to spaces so the record emits as one line."""
        def _sanitize(value: object) -> str:
            return str(value).replace("\n", " ").replace("\r", " ").strip()

        exc_text = getattr(record, "exc_text", None)
        if exc_text is not None:
            lines = exc_text.splitlines()
            record.exc_text = " | ".join(_sanitize(line) for line in lines if line.strip())
        if getattr(record, "message" , None) is not None:
            record.message = _sanitize(record.message)

        return record


class SparkBaseFormatter(SparkBaseFormatMixin, logging.Formatter):
    """
    stdlib ``logging.Formatter`` subclass with LogSpark traceback policy support.

    Applies ``process_spark_log_record()`` before delegating to the standard
    ``format()`` implementation. Used as the default formatter for
    ``SparkTerminalHandler`` when color is disabled or unavailable.
    """

    _tb_policy: TracebackOptions | None = None
    _multiline: bool = True

    def __init__(self,
                     fmt: str | None = None,
                     datefmt: str | None = None,
                     style: Literal["%", "{", "$"] = "%",
                     validate: bool = True,
                     *,
                     defaults: Mapping[str, Any] | None = None,
                     tb_policy: TracebackOptions | None = None,
                 multiline: bool = True,
                 **kwargs):
        """Initialize with format string, date format, traceback policy, and multiline flag."""
        super().__init__(fmt, datefmt, style, validate, defaults=defaults)
        self._tb_policy = tb_policy
        self._multiline = multiline

    def format(self, record: logging.LogRecord) -> str:
        """Apply traceback policy then delegate to stdlib Formatter.format()."""
        record = self.process_spark_log_record(record, self._multiline, self._tb_policy)
        return super().format(record)
