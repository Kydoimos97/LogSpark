"""Tests for SparkBaseFormatMixin exception formatting methods."""

import logging
import sys
from pathlib import Path

import pytest

from logspark.Formatters.SparkBaseFormatter import SparkBaseFormatMixin
from logspark.Types.Options import TracebackOptions
from logspark.Types.SparkRecordAttrs import SparkRecordAttrs


def _make_exc_attrs(with_tb: bool = True) -> SparkRecordAttrs:
    try:
        raise ValueError("test error")
    except ValueError:
        exc_type, exc_value, tb = sys.exc_info()
        return SparkRecordAttrs(
            filename="test.py",
            filepath=Path("test.py"),
            lineno=42,
            function="test_func",
            uri=None,
            exc_type=exc_type,
            exc_value=exc_value,
            exc_traceback=tb if with_tb else None,
        )


class TestGetSingleLineTb:
    """Test _get_single_line_tb returns correct single-line text."""

    def test_hide_policy_returns_basic_format(self):
        """Test HIDE policy returns exception type and value only."""
        attrs = _make_exc_attrs()
        result = SparkBaseFormatMixin._get_single_line_tb(attrs, TracebackOptions.HIDE)
        assert "ValueError" in result
        assert "test error" in result
        assert "\n" not in result

    def test_compact_policy_returns_location(self):
        """Test COMPACT policy returns default text with file and function."""
        attrs = _make_exc_attrs()
        result = SparkBaseFormatMixin._get_single_line_tb(attrs, TracebackOptions.COMPACT)
        assert "ValueError" in result
        assert "\n" not in result

    def test_full_policy_with_traceback_returns_content(self):
        """Test FULL policy with traceback returns non-empty string."""
        attrs = _make_exc_attrs(with_tb=True)
        result = SparkBaseFormatMixin._get_single_line_tb(attrs, TracebackOptions.FULL)
        assert result is not None
        assert "ValueError" in result


class TestGetMultilineTb:
    """Test _get_multiline_tb returns correct text."""

    def test_hide_policy_returns_basic_format(self):
        """Test HIDE policy returns exception type and value."""
        attrs = _make_exc_attrs()
        result = SparkBaseFormatMixin._get_multiline_tb(attrs, TracebackOptions.HIDE)
        assert result is not None
        assert "ValueError" in result
        assert "test error" in result

    def test_compact_policy_includes_location(self):
        """Test COMPACT policy includes file and line number."""
        attrs = _make_exc_attrs()
        result = SparkBaseFormatMixin._get_multiline_tb(attrs, TracebackOptions.COMPACT)
        assert result is not None
        assert "ValueError" in result
        assert "test.py" in result
        assert "42" in result

    def test_full_policy_returns_none(self):
        """FULL policy in multiline mode returns None to allow Rich/stdlib rendering."""
        attrs = _make_exc_attrs()
        result = SparkBaseFormatMixin._get_multiline_tb(attrs, TracebackOptions.FULL)
        assert result is None


class TestCollapseToSingleLine:
    """Test _collapse_to_single_line flattens record fields."""

    def test_collapses_exc_text_newlines(self):
        """Test that newlines in exc_text are replaced with pipe separators."""
        record = logging.LogRecord("test", logging.ERROR, "test.py", 1, "msg", (), None)
        record.exc_text = "line1\nline2\nline3"
        result = SparkBaseFormatMixin._collapse_to_single_line(record)
        assert "\n" not in result.exc_text
        assert "line1" in result.exc_text
        assert " | " in result.exc_text

    def test_none_exc_text_is_preserved(self):
        """Test that None exc_text is left as None."""
        record = logging.LogRecord("test", logging.INFO, "test.py", 1, "msg", (), None)
        record.exc_text = None
        result = SparkBaseFormatMixin._collapse_to_single_line(record)
        assert result.exc_text is None

    def test_returns_same_record(self):
        """Test that the same record object is returned."""
        record = logging.LogRecord("test", logging.INFO, "test.py", 1, "msg", (), None)
        result = SparkBaseFormatMixin._collapse_to_single_line(record)
        assert result is record