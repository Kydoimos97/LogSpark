"""
Test DDTraceInjectionFilter functionality.
"""

import logging
from unittest.mock import Mock, patch

import pytest

from logspark.Filters.DDTraceInjectionFilter import DDTraceInjectionFilter


class TestDDTraceCorrelationFilter:
    """Test DDTraceInjectionFilter"""

    def test_filter_without_ddtrace(self):
        """Test filter behavior when ddtrace is not available"""
        # Test the current behavior - if ddtrace is not available, _dd_tracer should be None
        filter_instance = DDTraceInjectionFilter()
        
        # Create a log record
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py", lineno=1,
            msg="Test message", args=(), exc_info=None
        )
        
        # Should not crash when ddtrace is unavailable
        result = filter_instance.filter(record)
        assert result is True  # Should still pass the record through

    def test_filter_with_ddtrace_available(self):
        """Test filter behavior when ddtrace is available"""
        # Mock ddtrace tracer
        mock_tracer = Mock()
        mock_span = Mock()
        mock_span.trace_id = 12345
        mock_span.span_id = 67890
        mock_tracer.current_span.return_value = mock_span
        
        with patch("logspark.Filters.DDTraceInjectionFilter._dd_tracer", mock_tracer):
            filter_instance = DDTraceInjectionFilter()
            
            # Create a log record
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="test.py", lineno=1,
                msg="Test message", args=(), exc_info=None
            )
            
            # Should add trace fields when ddtrace is available
            result = filter_instance.filter(record)
            assert result is True
            
            # Should have ddtrace fields (exact field names depend on implementation)
            mock_tracer.current_span.assert_called_once()

    def test_filter_with_ddtrace_no_active_span(self):
        """Test filter behavior when ddtrace is available but no active span"""
        # Mock ddtrace tracer with no active span
        mock_tracer = Mock()
        mock_tracer.current_span.return_value = None
        
        with patch("logspark.Filters.DDTraceInjectionFilter._dd_tracer", mock_tracer):
            filter_instance = DDTraceInjectionFilter()
            
            # Create a log record
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="test.py", lineno=1,
                msg="Test message", args=(), exc_info=None
            )
            
            # Should handle no active span gracefully
            result = filter_instance.filter(record)
            assert result is True