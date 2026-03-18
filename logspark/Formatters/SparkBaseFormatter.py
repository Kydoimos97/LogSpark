import logging
from traceback import format_exception
from typing import Literal, Mapping, Any

from ..Types.SparkRecordAttrs import is_spark_exception_enabled, has_spark_extra_attributes, SparkRecordAttrs
from ..Types.Options import TracebackOptions


class SparkBaseFormatMixin:

    @classmethod
    def process_spark_log_record(cls, record: logging.LogRecord, multiline: bool = True, traceback_policy: TracebackOptions | None = None):
        try:
            if is_spark_exception_enabled(record) and has_spark_extra_attributes(record):
                if record.spark.is_exception:
                    if multiline:
                        exc_text = cls._get_multiline_tb(record.spark, traceback_policy)
                    else:
                        exc_text = cls._get_single_line_tb(record.spark, traceback_policy)
                    record.exc_text = exc_text
                    record.exc_info = None
        except Exception:
            pass

        if not multiline:
            record = cls._collapse_to_single_line(record)

        return record

    @staticmethod
    def _get_multiline_tb(
        spark_attrs: SparkRecordAttrs,
        traceback_policy: TracebackOptions | None,
    ) -> None:

        exc_text = None
        if traceback_policy == TracebackOptions.HIDE:
            # Hide the traceback not the log
            exc_text = f"{spark_attrs.exc_name}: {spark_attrs.exc_value}"
        elif traceback_policy == TracebackOptions.COMPACT:
            # Format compact traceback for terminal display
            try:
                compact_tb = (
                    f'{spark_attrs.exc_name}: {spark_attrs.exc_value}\n      At "{spark_attrs.filename}:{spark_attrs.lineno}"'
                )

                if spark_attrs.name:
                    compact_tb += f", in {spark_attrs.name}"
                exc_text = compact_tb
            except Exception:
                # Fallback if traceback processing fails
                exc_text = f"{spark_attrs.exc_name}: {spark_attrs.exc_value}"

        return exc_text

    @staticmethod
    def _get_single_line_tb(
            spark_attrs: SparkRecordAttrs, traceback_policy: TracebackOptions | None,
    ) -> None:

        def _sanitize(value: object) -> str:
            return str(value).replace("\n", " ").replace("\r", " ").strip()

        default_text = f"{spark_attrs.exc_name}: {_sanitize(spark_attrs.exc_value)} | {spark_attrs.filename}:{spark_attrs.lineno} in {spark_attrs.name}"

        # remove exc info as we handle all of it
        if traceback_policy == TracebackOptions.HIDE or not spark_attrs.is_exception:
            # Hide the traceback not the log
            exc_text = f"{spark_attrs.exc_name}: {_sanitize(spark_attrs.exc_value)}"
        elif traceback_policy == TracebackOptions.FULL and spark_attrs.exc_traceback is not None:
            try:
                exc_text = "\n".join(format_exception(spark_attrs.exc_type, spark_attrs.exc_value, spark_attrs.exc_traceback))
            except Exception:
                pass
        else:
            exc_text = default_text

        return exc_text

    @staticmethod
    def _collapse_to_single_line(record: logging.LogRecord) -> logging.LogRecord:
        def _sanitize(value: object) -> str:
            return str(value).replace("\n", " ").replace("\r", " ").strip()

        if getattr(record, "exc_text", None) is not None:
            lines = record.exc_text.splitlines()
            record.exc_text = " | ".join(_sanitize(line) for line in lines if line.strip())
        if getattr(record, "message" , None) is not None:
            record.message = _sanitize(record.message)

        return record


class SparkBaseFormatter(SparkBaseFormatMixin, logging.Formatter):

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
        super().__init__(fmt, datefmt, style, validate, defaults=defaults)
        self._tb_policy = tb_policy
        self._multiline = multiline
