import logging

from ..Types.SparkRecordAttrs import SparkRecordAttrs, has_spark_extra_attributes


class TracebackPolicyFilter(logging.Filter):
    """
    Filter that attaches ``SparkRecordAttrs`` and enables the traceback policy flag.

    Populates ``record.spark`` from the record's exc_info (if not already set)
    and sets ``record._spark_exc = True`` to signal downstream formatters that
    traceback policy rendering is active for this record. Always returns True.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Attach SparkRecordAttrs and set the traceback policy flag; always returns True."""
        # Per Record override fall back is initial enable flag
        # this is set for the protocol, normally spark_exc is never set future hook possibly
        if not has_spark_extra_attributes(record):
            record.spark = SparkRecordAttrs.from_record(record)


        record._spark_exc = True # Protocol Flag highest record level no assumptions

        return True
