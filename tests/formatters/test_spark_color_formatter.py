"""
Test SparkColorFormatter functionality.
"""

import logging

from logspark.Formatters.SparkColorFormatter import SparkColorFormatter


class TestSparkColorFormatter:
    """Test SparkColorFormatter"""

    def test_debug_level_formatting(self):
        """Test DEBUG level gets gray badge and dim message"""
        formatter = SparkColorFormatter()
        record = logging.LogRecord(
            name="test", level=logging.DEBUG, pathname="test.py", lineno=1,
            msg="Debug message", args=(), exc_info=None
        )

        formatted = formatter.format(record)
        assert "\033[36m" in formatted  # cyan badge
        assert "\033[90m" in formatted  # gray (timestamp, path, message)
        assert "\033[0m" in formatted
        assert "Debug message" in formatted

    def test_warning_level_formatting(self):
        """Test WARNING level gets yellow badge and yellow message"""
        formatter = SparkColorFormatter()
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="test.py", lineno=1,
            msg="Warning message", args=(), exc_info=None
        )

        formatted = formatter.format(record)
        assert "\033[33m" in formatted  # yellow
        assert "\033[0m" in formatted
        assert "Warning message" in formatted

    def test_error_level_formatting(self):
        """Test ERROR level gets red badge and red message"""
        formatter = SparkColorFormatter()
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="test.py", lineno=1,
            msg="Error message", args=(), exc_info=None
        )

        formatted = formatter.format(record)
        assert "\033[31m" in formatted  # red
        assert "\033[0m" in formatted
        assert "Error message" in formatted

    def test_critical_level_formatting(self):
        """Test CRITICAL level gets bold magenta badge and magenta message"""
        formatter = SparkColorFormatter()
        record = logging.LogRecord(
            name="test", level=logging.CRITICAL, pathname="test.py", lineno=1,
            msg="Critical message", args=(), exc_info=None
        )

        formatted = formatter.format(record)
        assert "\033[1;35m" in formatted  # bold magenta badge
        assert "\033[35m" in formatted    # magenta message
        assert "\033[0m" in formatted
        assert "Critical message" in formatted

    def test_info_level_badge_and_gray_fields(self):
        """Test INFO level gets green badge; timestamp and path are gray; message is unstyled"""
        formatter = SparkColorFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py", lineno=1,
            msg="Info message", args=(), exc_info=None
        )

        formatted = formatter.format(record)
        assert "\033[32m" in formatted   # green badge
        assert "\033[90m" in formatted   # gray timestamp and path
        assert "\033[31m" not in formatted  # no red
        assert "\033[33m" not in formatted  # no yellow
        assert "Info message" in formatted

    def test_unknown_level_gray_fields_no_badge_color(self):
        """Test unknown level has gray timestamp and path but no level-specific badge or message color"""
        formatter = SparkColorFormatter()
        record = logging.LogRecord(
            name="test", level=25, pathname="test.py", lineno=1,
            msg="Custom message", args=(), exc_info=None
        )

        formatted = formatter.format(record)
        assert "\033[90m" in formatted   # gray timestamp and path always present
        assert "\033[31m" not in formatted  # no red
        assert "\033[33m" not in formatted  # no yellow
        assert "\033[35m" not in formatted  # no magenta
        assert "Custom message" in formatted

    def test_fmt_param_ignored_per_field_rendering_applies(self):
        """Test that fmt= is a no-op — per-field rendering is always used"""
        formatter = SparkColorFormatter(fmt="%(levelname)s: %(message)s")
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="test.py", lineno=1,
            msg="Error message", args=(), exc_info=None
        )

        formatted = formatter.format(record)
        assert "\033[31m" in formatted  # red present
        assert "\033[0m" in formatted
        assert "Error message" in formatted
