import logging
from typing import Any, Iterable, Literal, Mapping

from ..Formatters.SparkBaseFormatter import SparkBaseFormatter
from ..Types.Options import TracebackOptions
from ..Types.SparkRecordAttrs import has_spark_extra_attributes

# Record attributes that never reach the JSON output unless ``drop_fields`` says otherwise.
# uvicorn passes ``color_message``, its message with ANSI colour codes, as an extra on its
# start-up and access lines.
DEFAULT_DROPPED_FIELDS: tuple[str, ...] = ("color_message",)


class SparkJsonFormatter(SparkBaseFormatter):
    """
    JSON formatter that enforces a strict single-line-per-record invariant.

    Delegates serialisation to ``pythonjsonlogger.json.JsonFormatter`` (lazy
    import inside ``__init__``). Before serialising, exc_info and exc_text are
    collapsed or cleared according to the traceback policy, and internal
    LogSpark attributes (``spark``, ``_spark_exc``) are stripped so they never
    appear in JSON output.

    When a record carries ``SparkRecordAttrs`` (set by ``PathNormalizationFilter``
    or ``TracebackPolicyFilter``), the path it resolved is written as the
    ``filepath`` key, in POSIX form. ``filename`` keeps its stdlib meaning, the
    base name. A ``filepath`` passed with ``extra=`` on the log call wins.

    ``drop_fields`` names record attributes that are left out of the output;
    the default is ``DEFAULT_DROPPED_FIELDS``. Pass an empty collection to keep
    everything. The record itself is not changed, so other handlers still see
    those attributes.

    Raises ``ImportError`` at construction time when python-json-logger is absent
    (caught and re-raised as ``MissingDependencyException`` by ``SparkJsonHandler``).
    """

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        style: Literal["%", "{", "$"] = "%",
        validate: bool = True,
        *,
        defaults: Mapping[str, Any] | None = None,
        tb_policy: TracebackOptions | None = None,
        drop_fields: Iterable[str] | None = None,
        **kwargs,
    ):
        """Initialize with the json-logger backend; multiline is always False for JSON output."""
        super().__init__(
            fmt, datefmt, style, validate, defaults=defaults, tb_policy=tb_policy, multiline=False
        )

        from pythonjsonlogger.core import RESERVED_ATTRS
        from pythonjsonlogger.json import JsonFormatter

        dropped = DEFAULT_DROPPED_FIELDS if drop_fields is None else tuple(drop_fields)
        reserved = kwargs.pop("reserved_attrs", None)
        kwargs["reserved_attrs"] = [*(RESERVED_ATTRS if reserved is None else reserved), *dropped]

        kwargs.setdefault("json_ensure_ascii", False)
        self._json_formatter = JsonFormatter(
            fmt=fmt, datefmt=datefmt, style=style, validate=validate, defaults=defaults, **kwargs
        )

    def format(self, record: logging.LogRecord) -> str:
        """Apply traceback policy, strip internal attributes, and emit a single-line JSON string."""
        record = self.process_spark_log_record(record, self._multiline, self._tb_policy)

        # Enforce single-line invariant on exc field values.
        # process_spark_log_record handles SparkRecordAttrs records and clears exc_info.
        # For plain records, read traceback_policy from the record (if set) then collapse
        # or suppress so that no embedded newlines appear in JSON field values.
        tb_policy = getattr(record, "traceback_policy", self._tb_policy)
        if record.exc_info:
            if tb_policy == TracebackOptions.HIDE:
                record.exc_info = None
                record.exc_text = None
            else:
                if not record.exc_text:
                    record.exc_text = self.formatException(record.exc_info)
                record.exc_text = record.exc_text.replace("\n", " ").replace("\r", " ").strip()
                record.exc_info = None
        elif record.exc_text:
            if tb_policy == TracebackOptions.HIDE:
                record.exc_text = None
            else:
                record.exc_text = record.exc_text.replace("\n", " ").replace("\r", " ").strip()

        # Remove Spark-internal attributes before JSON serialization.
        # SparkRecordAttrs contains TracebackType which is not JSON-serializable,
        # and _spark_exc is an internal protocol flag not intended for output.
        # The resolved path goes out as ``filepath`` for the duration of the serialisation only,
        # so the attribute does not leak to other handlers of the same record.
        adds_filepath = has_spark_extra_attributes(record) and "filepath" not in record.__dict__
        if adds_filepath:
            record.__dict__["filepath"] = record.__dict__["spark"].filepath.as_posix()
        record.__dict__.pop("spark", None)
        record.__dict__.pop("_spark_exc", None)
        try:
            formatted: str = self._json_formatter.format(record)
        finally:
            if adds_filepath:
                record.__dict__.pop("filepath", None)

        # Physical single-line invariant (JSON-safe newlines in raw output).
        return formatted.replace("\n", " ").replace("\r", " ").strip()
