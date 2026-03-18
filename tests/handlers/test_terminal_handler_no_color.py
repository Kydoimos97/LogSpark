"""Tests for SparkTerminalHandler with use_color=False (lines 173-175)."""

import io

from logspark.Handlers.SparkTerminalHandler import SparkTerminalHandler


class TestSparkTerminalHandlerNoColor:
    """Test SparkTerminalHandler with use_color=False."""

    def test_null_highlighter_when_use_color_false(self):
        """Test that NullHighlighter is used when use_color=False (lines 173-175)."""
        stream = io.StringIO()

        # Create handler with use_color=False
        handler = SparkTerminalHandler(stream=stream, use_color=False)

        # Handler should be created successfully
        assert handler is not None

        # The internal rich handler should have NullHighlighter
        # We can verify this by checking that the handler works without color
        import logging
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="test message",
            args=(),
            exc_info=None
        )

        # Should emit without error
        handler.emit(record)

        # Check that output was written to stream
        output = stream.getvalue()
        assert "test message" in output
        # Should not contain ANSI color codes when use_color=False
        assert "\x1b[" not in output  # No ANSI escape sequences
