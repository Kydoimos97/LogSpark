import logging

from ..Types.SparkRecordAttrs import (
    SparkRecordAttrs, has_spark_extra_attributes)


class TracebackPolicyFilter(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Inject ddtrace correlation fields if ddtrace is active

        Args:
            record: LogRecord to potentially enrich

        Returns:
            True (always allow record to pass through)
        """
        # Per Record override fall back is initial enable flag
        # this is set for the protocol, normally spark_exc is never set future hook possibly
        if not has_spark_extra_attributes(record):
            record.spark = SparkRecordAttrs.from_record(record)


        record._spark_exc = True # Protocol Flag highest record level no assumptions

        return True
