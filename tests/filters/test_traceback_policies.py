"""
Test TracebackPolicyFilter behavior.

This module tests that TracebackPolicyFilter correctly enriches log records
with spark attributes and sets the exception origin flag.
"""

import logging
import sys
from pathlib import Path

from logspark.Filters.TracebackPolicyFilter import TracebackPolicyFilter
from logspark.Types.Options import TracebackOptions
from logspark.Types.SparkRecordAttrs import SparkRecordAttrs, has_spark_extra_attributes


class TestTracebackPolicyFilterBasics:
    """Test TracebackPolicyFilter sets correct record attributes."""

    def test_filter_sets_spark_exc_flag(self):
        """Test that filter sets _spark_exc = True on records."""
        f = TracebackPolicyFilter()
        record = logging.LogRecord("test", logging.INFO, "test.py", 1, "msg", (), None)
        f.filter(record)
        assert getattr(record, "_spark_exc", False) is True

    def test_filter_creates_spark_attrs_if_missing(self):
        """Test that filter creates record.spark if not already present."""
        f = TracebackPolicyFilter()
        record = logging.LogRecord("test", logging.INFO, "test.py", 1, "msg", (), None)
        assert not hasattr(record, "spark")
        f.filter(record)
        assert has_spark_extra_attributes(record)
        assert isinstance(record.spark, SparkRecordAttrs)

    def test_filter_does_not_overwrite_existing_spark(self):
        """Test that filter preserves spark attrs already set on the record."""
        f = TracebackPolicyFilter()
        record = logging.LogRecord("test", logging.INFO, "test.py", 1, "msg", (), None)
        existing = SparkRecordAttrs(
            filename="existing.py",
            filepath=Path("existing.py"),
            lineno=99,
            function="existing_func",
            uri=None,
            exc_type=None,
            exc_value=None,
        )
        record.spark = existing
        f.filter(record)
        assert record.spark is existing

    def test_filter_always_returns_true(self):
        """Test that filter always allows records to pass through."""
        f = TracebackPolicyFilter()
        for level in [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]:
            record = logging.LogRecord("test", level, "test.py", 1, "msg", (), None)
            assert f.filter(record) is True

    def test_filter_works_with_exception_record(self):
        """Test that filter handles exception records correctly."""
        f = TracebackPolicyFilter()
        try:
            raise ValueError("test")
        except ValueError:
            record = logging.LogRecord(
                "test", logging.ERROR, "test.py", 1, "msg", (), sys.exc_info()
            )
        result = f.filter(record)
        assert result is True
        assert getattr(record, "_spark_exc", False) is True
        assert has_spark_extra_attributes(record)
        assert record.spark.is_exception

    def test_filter_with_no_exception(self):
        """Test that filter works correctly on records with no exception."""
        f = TracebackPolicyFilter()
        record = logging.LogRecord("test", logging.INFO, "test.py", 1, "msg", (), None)
        result = f.filter(record)
        assert result is True
        assert getattr(record, "_spark_exc", False) is True
        assert has_spark_extra_attributes(record)
        assert not record.spark.is_exception


class TestTracebackPolicyFilterRecordPreservation:
    """Test that TracebackPolicyFilter does not mutate core record fields."""

    def test_filter_preserves_message(self):
        """Test that filter does not alter the record message."""
        f = TracebackPolicyFilter()
        record = logging.LogRecord("test", logging.INFO, "test.py", 42, "original message", (), None)
        f.filter(record)
        assert record.msg == "original message"

    def test_filter_preserves_level(self):
        """Test that filter does not alter the record level."""
        f = TracebackPolicyFilter()
        record = logging.LogRecord("test", logging.WARNING, "test.py", 1, "msg", (), None)
        f.filter(record)
        assert record.levelno == logging.WARNING

    def test_filter_preserves_name(self):
        """Test that filter does not alter the logger name."""
        f = TracebackPolicyFilter()
        record = logging.LogRecord("my.logger", logging.INFO, "test.py", 1, "msg", (), None)
        f.filter(record)
        assert record.name == "my.logger"

    def test_filter_preserves_lineno(self):
        """Test that filter does not alter the line number."""
        f = TracebackPolicyFilter()
        record = logging.LogRecord("test", logging.INFO, "test.py", 99, "msg", (), None)
        f.filter(record)
        assert record.lineno == 99
