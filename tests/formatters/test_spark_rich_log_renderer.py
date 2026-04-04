"""Tests for SparkRichFormatter coverage (lines 193, 293, 312, 360)."""

import logging

import pytest

pytest.importorskip("rich")
from logspark.Handlers.Rich.SparkRichHandler import SparkRichHandler


class TestSparkRichLogRenderer:
    """Test SparkRichFormatter coverage through SparkRichHandler."""

    def test_time_column_else_branch_with_show_time(self):
        """Test time column else branch when show_time=True (line 193)."""
        handler = SparkRichHandler(show_time=True)

        # Create a record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="test message",
            args=(),
            exc_info=None
        )

        # Emit the record - this should exercise the renderer's time column logic
        handler.emit(record)

        # Should successfully emit without error
        assert True  # If we get here, the emit worked

    def test_rich_handler_with_various_options(self):
        """Test SparkRichHandler with various options to exercise renderer paths."""
        handler = SparkRichHandler(
            show_time=True,
            show_path=True,
            show_function=True,
            show_level=True
        )

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/very/long/path/to/test/file.py",
            lineno=42,
            msg="test message with lots of content to test width calculations",
            args=(),
            exc_info=None
        )

        # This should exercise various renderer code paths
        handler.emit(record)

        # Should successfully emit without error
        assert True  # If we get here, the emit worked

    def test_rich_log_render_invalid_console(self):
        from logspark.Formatters.Rich.SparkRichFormatter import SparkRichFormatter
        from rich.console import Console
        from rich.text import Text

        console = Console(width="nan")

        assert console.width == "nan"

        renderer = SparkRichFormatter(show_function = True, show_path = True)

        renderable = Text('1234567890')

        with pytest.raises(TypeError):
            message_width, path_width, function_width, show_arrow = renderer._assign_variable_widths(console, renderable, renderable, renderable, renderable)


    def test_rich_log_assign_function_width(self):
        from logspark.Formatters.Rich.SparkRichFormatter import SparkRichFormatter
        from rich.console import Console
        from rich.text import Text

        console = Console()

        renderer = SparkRichFormatter(show_function = True, show_path = True)

        message_width, time_width, path_width, function_width = renderer._assign_variable_widths(console, None, None, None, Text('funky_function'))

        assert function_width == len('funky_function')

    def test_rich_log_no_last_time(self):
        from logspark.Formatters.Rich.SparkRichFormatter import SparkRichFormatter
        from rich.console import Console
        from rich.text import Text

        console = Console()

        renderer = SparkRichFormatter(show_function = True, show_path = True)
        renderer._last_time = None
        renderable = Text('Test123')

        renderer.__call__(
                console = console,
                renderables=renderable
                )

        assert renderer._last_time is not None