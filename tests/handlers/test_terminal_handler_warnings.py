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
        from rich.console import Console

        # Create non-terminal console
        non_terminal_console = Console(force_terminal=False, file=io.StringIO())

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            SparkTerminalHandler(use_color=True)

            # Should emit RichColorDegradedWarning
            color_warnings = [
                warning for warning in w
                if "FORCE_COLOR=true".lower() in str(warning.message).lower()
            ]
            assert len(color_warnings) >= 1

    def test_ansi_color_degraded_warning(self):
        """Test AnsiColorDegradedWarning when stdlib console doesn't support colors"""
        with patch("logspark._Internal.Func.is_color_compatible_terminal.is_color_compatible_terminal", return_value=False):
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

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            SparkTerminalHandler(log_time_format="%invalid_format%")

            # Should emit InvalidTimeFormatWarning and fall back to default
            time_warnings = [
                warning for warning in w
                if "timeformat" in str(warning.message).lower()
            ]
            assert len(time_warnings) >= 1

    def test_invalid_time_format_warning_stdlib(self):
        """Test InvalidTimeFormatWarning for stdlib handler with invalid format"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            SparkTerminalHandler(log_time_format="%invalid_format%")

            # Should emit InvalidTimeFormatWarning and fall back to default
            time_warnings = [
                warning for warning in w
                if "timeformat" in str(warning.message).lower()
            ]
            assert len(time_warnings) >= 1

    def test_callable_time_format_rich_only(self):
        """Test that callable time formats work only with Rich"""
        pytest.importorskip("rich")

        def custom_time_format(dt):
            return f"Custom: {dt.strftime('%H:%M:%S')}"

        # Should work with Rich
        handler_rich = SparkTerminalHandler(log_time_format=custom_time_format)
        assert callable(handler_rich._handler._spark_formatter.time_format)

        # Should be rejected for stdlib and fall back to default with warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            handler_stdlib = SparkTerminalHandler(log_time_format=custom_time_format)

            # Should emit warning about invalid time format (callable not supported for stdlib)
            time_warnings = [
                warning for warning in w
                if "timeformat" in str(warning.message).lower()
            ]
            assert len(time_warnings) >= 1

            # Should fall back to default string format
            formatter = handler_stdlib._handler.formatter
            assert formatter is not None

            # Verify it uses default time format by checking a formatted record
            import logging
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="test.py", lineno=1,
                msg="Test message", args=(), exc_info=None
            )
            formatted = formatter.format(record)
            assert isinstance(formatted, str)
            # Should contain default time format pattern (not custom format)
            assert "Custom:" not in formatted


class TestSparkTerminalHandlerBranchingBehavior:
    """Test Rich vs stdlib branching behavior"""

    def test_rich_branch_selection(self):
        """Test that Rich branch is selected when available and not disabled"""
        pytest.importorskip("rich")

        handler = SparkTerminalHandler()

        # Should use Rich handler
        from logspark.Handlers.Rich.SparkRichHandler import SparkRichHandler
        assert isinstance(handler._handler, SparkRichHandler)

    def test_stdlib_branch_selection(self):
        """Test that stdlib branch is selected when Rich is disabled"""
        handler = SparkTerminalHandler()

        # Should use stdlib StreamHandler
        assert isinstance(handler._handler, logging.StreamHandler)
        assert not hasattr(handler._handler, "_c_log_render")

    def test_rich_disabled_forces_stdlib(self):
        """Test that no_rich=True forces stdlib even if Rich is available"""
        pytest.importorskip("rich")

        handler = SparkTerminalHandler()

        # Should use stdlib handler despite Rich being available
        assert isinstance(handler._handler, logging.StreamHandler)

    def test_stdlib_format_generation(self):
        """Test stdlib format string generation with different options"""
        handler = SparkTerminalHandler(show_time=True, show_level=True, show_path=True, show_function=True, level_width=10)

        # Should have formatter with expected format
        formatter = handler._handler.formatter
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
                assert isinstance(handler._handler.formatter, SparkColorFormatter)

    def test_plain_formatter_when_not_viable(self):
        """Test that plain formatter is used when output surface is not viable"""
        with patch("logspark._Internal.Func.is_color_compatible_terminal.is_color_compatible_terminal", return_value=False):
            handler = SparkTerminalHandler(use_color=True)

            # Should use plain Formatter
            assert isinstance(handler._handler.formatter, logging.Formatter)
            from logspark.Formatters import SparkColorFormatter
            assert not isinstance(handler._handler.formatter, SparkColorFormatter)

    def test_color_formatter_level_colors(self):
        """Test that SparkColorFormatter applies correct colors"""
        with patch("logspark._Internal.Func.is_color_compatible_terminal.is_color_compatible_terminal", return_value=True):
            handler = SparkTerminalHandler(use_color=True)

            formatter = handler._handler.formatter
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
