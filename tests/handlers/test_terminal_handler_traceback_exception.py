"""Tests for SparkTerminalHandler traceback exception handling (lines 279-281)."""

import logging
import sys
from unittest.mock import Mock, patch

from logspark.Handlers.SparkTerminalHandler import SparkTerminalHandler
from logspark.Types.Options import TracebackOptions


class TestSparkTerminalHandlerTracebackException:
    """Test SparkTerminalHandler traceback exception handling."""

    def test_traceback_processing_exception_fallback(self):
        """Test fallback when traceback processing fails (lines 279-281)."""
        handler = SparkTerminalHandler()

        # Create a record with exception info
        try:
            raise ValueError("test error")
        except ValueError:
            exc_type, exc_value, tb = sys.exc_info()

            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=42,
                msg="test message",
                args=(),
                exc_info=(exc_type, exc_value, tb)
            )

            # Set traceback policy to COMPACT to trigger the processing
            record.traceback_policy = TracebackOptions.COMPACT

            # Mock traceback.extract_tb to raise an exception
            with patch("traceback.extract_tb", side_effect=Exception("Mock traceback error")):
                handler.emit(record)

                # Should fall back to basic format
                assert record.exc_text == "ValueError: test error"
                assert record.exc_info is None  # Should be cleared

    def test_filter_management_methods(self):
        """Test addFilter and removeFilter methods (lines 307-308)."""
        handler = SparkTerminalHandler()

        # Create a mock filter
        mock_filter = Mock()

        # Test addFilter
        handler.addFilter(mock_filter)

        # Verify filter was added to both handlers
        assert mock_filter in handler.filters
        assert mock_filter in handler._handler.filters

        # Test removeFilter
        handler.removeFilter(mock_filter)

        # Verify filter was removed from both handlers
        assert mock_filter not in handler.filters
        assert mock_filter not in handler._handler.filters
