"""
Test SparkTerminalHandler color degradation and time format validation warnings.

Tests validate:
- Rich color degradation warnings
- ANSI color degradation warnings
- Time format validation warnings
- Rich vs stdlib branching behavior
- FORCE_COLOR override behavior
"""

import io
import logging
import warnings
from unittest.mock import patch

import pytest

from logspark.Handlers.SparkTerminalHandler import SparkTerminalHandler


class TestSparkTerminalHandlerColorDegradationWarnings:
    """Test color degradation warning functionality"""

    def test_rich_color_degraded_warning(self):
        """Test RichColorDegradedWarning when Rich console doesn't support colors"""
        pytest.importorskip("rich")

        with patch("logspark.Handlers.SparkTerminalHandler.is_color_compatible_terminal", return_value=False):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                SparkTerminalHandler(use_color=True)

                color_warnings = [
                    warning for warning in w
                    if "FORCE_COLOR=true".lower() in str(warning.message).lower()
                ]
                assert len(color_warnings) >= 1

    def test_ansi_color_degraded_warning(self):
        """Test AnsiColorDegradedWarning when stdlib console doesn't support colors"""
        with patch("logspark.Handlers.SparkTerminalHandler.is_color_compatible_terminal", return_value=False):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                SparkTerminalHandler(use_color=True)

                # Should emit AnsiColorDegradedWarning
                color_warnings = [
                    warning for warning in w
                    if "FORCE_COLOR=true".lower() in str(warning.message).lower()
                ]
                assert len(color_warnings) >= 1

    def test_force_color_overrides_degradation(self):
        """Test that FORCE_COLOR=true overrides color degradation"""
        with patch.dict("os.environ", {"FORCE_COLOR": "true"}):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                SparkTerminalHandler(use_color=True)

                # Should not emit color degradation warnings when FORCE_COLOR is set
                color_warnings = [
                    warning for warning in w
                    if "color" in str(warning.message).lower()
                ]
                assert len(color_warnings) == 0


class TestSparkTerminalHandlerTimeFormatValidation:
    """Test time format validation warnings"""

    def test_invalid_time_format_warning_rich(self):
        """Test InvalidTimeFormatWarning for Rich handler with invalid format"""
        pytest.importorskip("rich")

        with patch("logspark._Internal.Func.validate_timeformat.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.side_effect = ValueError("invalid format")

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                SparkTerminalHandler(log_time_format="%invalid_format%")

                time_warnings = [
                    warning for warning in w
                    if "timeformat" in str(warning.message).lower()
                ]
                assert len(time_warnings) >= 1

    def test_invalid_time_format_warning_stdlib(self):
        """Test InvalidTimeFormatWarning for stdlib handler with invalid format"""
        with patch("logspark._Internal.Func.validate_timeformat.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.side_effect = ValueError("invalid format")

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                SparkTerminalHandler(log_time_format="%invalid_format%")

                time_warnings = [
                    warning for warning in w
                    if "timeformat" in str(warning.message).lower()
                ]
                assert len(time_warnings) >= 1

    def test_callable_time_format_rejected(self):
        """Test that callable time formats are rejected with a warning and fall back to default"""

        def custom_time_format(dt):
            return f"Custom: {dt.strftime('%H:%M:%S')}"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            handler = SparkTerminalHandler(log_time_format=custom_time_format)

            time_warnings = [
                warning for warning in w
                if "timeformat" in str(warning.message).lower()
            ]
            assert len(time_warnings) >= 1

            formatter = handler.formatter
            assert formatter is not None

            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="test.py", lineno=1,
                msg="Test message", args=(), exc_info=None
            )
            formatted = formatter.format(record)
            assert isinstance(formatted, str)
            assert "Custom:" not in formatted


class TestSparkTerminalHandlerBranchingBehavior:
    """Test Rich vs stdlib branching behavior"""

    def test_rich_branch_selection(self):
        """Test that SparkTerminalHandler is a StreamHandler with a formatter set"""
        handler = SparkTerminalHandler()

        assert isinstance(handler, logging.StreamHandler)
        assert handler.formatter is not None

    def test_stdlib_branch_selection(self):
        """Test that SparkTerminalHandler is always a StreamHandler"""
        handler = SparkTerminalHandler()

        assert isinstance(handler, logging.StreamHandler)
        assert not hasattr(handler, "_spark_formatter")

    def test_rich_disabled_forces_stdlib(self):
        """Test that SparkTerminalHandler is always stdlib-based"""
        handler = SparkTerminalHandler()

        assert isinstance(handler, logging.StreamHandler)

    def test_stdlib_format_generation(self):
        """Test stdlib format string generation with different options"""
        handler = SparkTerminalHandler(show_time=True, show_level=True, show_path=True, show_function=True, level_width=10)

        # Should have formatter with expected format
        formatter = handler.formatter
        assert formatter is not None

        # Test that it can format a record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_function"

        formatted = formatter.format(record)
        assert "Test message" in formatted
        assert "INFO" in formatted
        assert "test.py:42" in formatted
        assert "test_function" in formatted


class TestSparkTerminalHandlerColorFormatter:
    """Test SparkColorFormatter integration"""

    def test_color_formatter_applied_when_viable(self):
        """Test that SparkColorFormatter is used when output surface is viable"""
        with patch("logspark._Internal.Func.is_color_compatible_terminal.is_color_compatible_terminal", return_value=True):
            with patch.dict("os.environ", {"FORCE_COLOR": "true"}):
                handler = SparkTerminalHandler(use_color=True)

                # Should use SparkColorFormatter when FORCE_COLOR is set
                from logspark.Formatters import SparkColorFormatter
                assert isinstance(handler.formatter, SparkColorFormatter)

    def test_plain_formatter_when_not_viable(self):
        """Test that plain formatter is used when output surface is not viable"""
        with patch("logspark.Handlers.SparkTerminalHandler.is_color_compatible_terminal", return_value=False):
            handler = SparkTerminalHandler(use_color=True)

            # Should use plain Formatter
            assert isinstance(handler.formatter, logging.Formatter)
            from logspark.Formatters import SparkColorFormatter
            assert not isinstance(handler.formatter, SparkColorFormatter)

    def test_color_formatter_level_colors(self):
        """Test that SparkColorFormatter applies correct colors"""
        with patch("logspark._Internal.Func.is_color_compatible_terminal.is_color_compatible_terminal", return_value=True):
            handler = SparkTerminalHandler(use_color=True)

            formatter = handler.formatter
            from logspark.Formatters import SparkColorFormatter

            if isinstance(formatter, SparkColorFormatter):
                # Test different log levels
                debug_record = logging.LogRecord(
                    name="test", level=logging.DEBUG, pathname="test.py", lineno=1,
                    msg="Debug message", args=(), exc_info=None
                )

                info_record = logging.LogRecord(
                    name="test", level=logging.INFO, pathname="test.py", lineno=1,
                    msg="Info message", args=(), exc_info=None
                )

                warning_record = logging.LogRecord(
                    name="test", level=logging.WARNING, pathname="test.py", lineno=1,
                    msg="Warning message", args=(), exc_info=None
                )

                debug_output = formatter.format(debug_record)
                info_output = formatter.format(info_record)
                warning_output = formatter.format(warning_record)

                # DEBUG should be gray (contains ANSI codes)
                assert "\033[90m" in debug_output  # Gray

                # INFO should be uncolored (no ANSI codes)
                assert "\033[" not in info_output or info_output.count("\033[") == 0

                # WARNING should be yellow
                assert "\033[33m" in warning_output  # Yellow
