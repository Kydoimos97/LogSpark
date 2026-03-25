"""Integration tests for SparkBaseFormatter.format() traceback policy application."""

import logging
import sys
from unittest.mock import patch

import pytest

from logspark.Filters.TracebackPolicyFilter import TracebackPolicyFilter
from logspark.Formatters.SparkBaseFormatter import SparkBaseFormatter
from logspark.Types.Options import TracebackOptions


def _make_exc_record() -> logging.LogRecord:
    """Return a LogRecord with real exc_info, processed through TracebackPolicyFilter."""
    try:
        raise ValueError("formatter test error")
    except ValueError:
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="something failed",
            args=(),
            exc_info=sys.exc_info(),
        )
    TracebackPolicyFilter().filter(record)
    return record


def _make_plain_record() -> logging.LogRecord:
    """Return a LogRecord with no exception."""
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="plain message",
        args=(),
        exc_info=None,
    )
    TracebackPolicyFilter().filter(record)
    return record


class TestSparkBaseFormatterFormat:

    def test_compact_policy_shows_type_and_location(self):
        """COMPACT renders exception type and single frame location."""
        fmt = SparkBaseFormatter(fmt="%(message)s", tb_policy=TracebackOptions.COMPACT)
        record = _make_exc_record()
        output = fmt.format(record)
        assert "ValueError" in output
        assert "formatter test error" in output
        assert "Traceback" not in output

    def test_hide_policy_shows_type_and_message_only(self):
        """HIDE renders only exception type and message — no location, no frames."""
        fmt = SparkBaseFormatter(fmt="%(message)s", tb_policy=TracebackOptions.HIDE)
        record = _make_exc_record()
        output = fmt.format(record)
        assert "ValueError" in output
        assert "formatter test error" in output
        assert "Traceback" not in output
        assert "test_spark_base_formatter" not in output

    def test_full_policy_shows_all_frames(self):
        """FULL renders the complete traceback including all frames."""
        fmt = SparkBaseFormatter(fmt="%(message)s", tb_policy=TracebackOptions.FULL)
        record = _make_exc_record()
        output = fmt.format(record)
        assert "ValueError" in output
        assert "formatter test error" in output
        assert "Traceback" in output

    def test_no_policy_shows_no_traceback(self):
        """No policy (None): exception info is cleared, nothing extra rendered."""
        fmt = SparkBaseFormatter(fmt="%(message)s", tb_policy=None)
        record = _make_exc_record()
        output = fmt.format(record)
        assert "something failed" in output
        assert "Traceback" not in output

    def test_plain_record_unaffected(self):
        """Records without exceptions are formatted normally regardless of policy."""
        fmt = SparkBaseFormatter(fmt="%(message)s", tb_policy=TracebackOptions.COMPACT)
        record = _make_plain_record()
        output = fmt.format(record)
        assert "plain message" in output

    def test_multiline_false_collapses_exc_text(self):
        """multiline=False collapses exc_text to a single line (no internal newlines)."""
        fmt = SparkBaseFormatter(
            fmt="%(message)s",
            tb_policy=TracebackOptions.COMPACT,
            multiline=False,
        )
        record = _make_exc_record()
        output = fmt.format(record)
        assert "ValueError" in output
        lines = output.split("\n")
        exc_line = lines[-1]
        assert "ValueError" in exc_line
        assert "\n" not in exc_line


class TestSparkBaseFormatMixinExceptionSuppression:

    def test_inner_exception_is_suppressed(self):
        """Errors raised inside process_spark_log_record are caught and discarded."""
        from logspark.Formatters.SparkBaseFormatter import SparkBaseFormatMixin

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="trigger",
            args=(),
            exc_info=None,
        )
        with patch(
            "logspark.Formatters.SparkBaseFormatter.is_spark_exception_enabled",
            side_effect=RuntimeError("internal failure"),
        ):
            result = SparkBaseFormatMixin.process_spark_log_record(record)
        assert result is record
