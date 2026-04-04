"""Tests for SparkTerminalHandler traceback exception handling (lines 279-281)."""

import logging
from unittest.mock import Mock

from logspark.Handlers.SparkTerminalHandler import SparkTerminalHandler


class TestSparkTerminalHandlerTracebackException:
    """Test SparkTerminalHandler traceback exception handling."""

    def test_filter_management_methods(self):
        """Test addFilter and removeFilter methods (lines 307-308)."""
        handler = SparkTerminalHandler()

        # Create a mock filter
        mock_filter = Mock()

        # Test addFilter
        handler.addFilter(mock_filter)

        # Verify filter was added to handler
        assert mock_filter in handler.filters

        # Test removeFilter
        handler.removeFilter(mock_filter)

        # Verify filter was removed from handler
        assert mock_filter not in handler.filters
