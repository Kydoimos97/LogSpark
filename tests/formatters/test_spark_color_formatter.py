"""
Test SparkColorFormatter functionality.
"""

import logging

from logspark.Formatters.SparkColorFormatter import SparkColorFormatter


class TestSparkColorFormatter:
    """Test SparkColorFormatter"""

    def test_debug_level_formatting(self):
        """Test DEBUG level gets gray color"""
        formatter = SparkColorFormatter()
        record = logging.LogRecord(
            name="test", level=logging.DEBUG, pathname="test.py", lineno=1,
            msg="Debug message", args=(), exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "\033[90m" in formatted  # gray color
        assert "\033[0m" in formatted   # reset
        assert "Debug message" in formatted

    def test_warning_level_formatting(self):
        """Test WARNING level gets yellow color"""
        formatter = SparkColorFormatter()
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="test.py", lineno=1,
            msg="Warning message", args=(), exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "\033[33m" in formatted  # yellow color
        assert "\033[0m" in formatted   # reset
        assert "Warning message" in formatted

    def test_error_level_formatting(self):
        """Test ERROR level gets red color"""
        formatter = SparkColorFormatter()
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="test.py", lineno=1,
            msg="Error message", args=(), exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "\033[31m" in formatted  # red color
        assert "\033[0m" in formatted   # reset
        assert "Error message" in formatted

    def test_critical_level_formatting(self):
        """Test CRITICAL level gets magenta color"""
        formatter = SparkColorFormatter()
        record = logging.LogRecord(
            name="test", level=logging.CRITICAL, pathname="test.py", lineno=1,
            msg="Critical message", args=(), exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "\033[35m" in formatted  # magenta color
        assert "\033[0m" in formatted   # reset
        assert "Critical message" in formatted

    def test_info_level_no_color(self):
        """Test INFO level remains unstyled"""
        formatter = SparkColorFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py", lineno=1,
            msg="Info message", args=(), exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "\033[" not in formatted  # No ANSI codes
        assert "Info message" in formatted

    def test_unknown_level_no_color(self):
        """Test unknown level remains unstyled"""
        formatter = SparkColorFormatter()
        record = logging.LogRecord(
            name="test", level=25, pathname="test.py", lineno=1,  # Custom level
            msg="Custom message", args=(), exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "\033[" not in formatted  # No ANSI codes
        assert "Custom message" in formatted

    def test_formatter_with_custom_format(self):
        """Test formatter with custom format string"""
        formatter = SparkColorFormatter(fmt="%(levelname)s: %(message)s")
        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="test.py", lineno=1,
            msg="Error message", args=(), exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "\033[31m" in formatted  # red color
        assert "\033[0m" in formatted   # reset
        assert "ERROR: Error message" in formatted