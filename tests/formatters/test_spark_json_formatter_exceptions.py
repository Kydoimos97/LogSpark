"""Tests for SparkJsonFormatter exception handling (lines 89, 97-99, 114, 117-118)."""

import sys
import traceback
from ..Types import TracebackType
from unittest.mock import Mock, patch

import pytest
from pythonjsonlogger.json import JsonFormatter

from logspark.Formatters.SparkJsonFormatter import SparkJsonFormatter


class TestSparkJsonFormatterExceptionHandling:
    """Test exception handling in SparkJsonFormatter methods."""

    def test_format_compact_exception_handling_line_89(self):
        """Test _format_compact exception handling (line 89)."""
        json_formatter = JsonFormatter()
        formatter = SparkJsonFormatter(json_formatter)
        
        # Create a mock traceback that will cause extract_tb to raise
        mock_tb = Mock(spec=TracebackType)
        
        with patch('traceback.extract_tb', side_effect=Exception("Mock error")):
            result = formatter._format_compact(ValueError, ValueError("test"), mock_tb)
            
            # Should fall back to basic format
            assert result == "ValueError: test"

    def test_format_compact_no_traceback_line_90(self):
        """Test _format_compact with None traceback (line 90)."""
        json_formatter = JsonFormatter()
        formatter = SparkJsonFormatter(json_formatter)
        
        result = formatter._format_compact(ValueError, ValueError("test"), None)
        assert result == "ValueError: test"

    def test_format_compact_empty_frames_line_97_99(self):
        """Test _format_compact with empty frames (lines 97-99)."""
        json_formatter = JsonFormatter()
        formatter = SparkJsonFormatter(json_formatter)
        
        # Mock extract_tb to return empty list
        with patch('traceback.extract_tb', return_value=[]):
            result = formatter._format_compact(ValueError, ValueError("test"), Mock())
            
            # Should fall back to basic format when no frames
            assert result == "ValueError: test"

    def test_format_full_exception_handling_line_114(self):
        """Test _format_full exception handling (line 114)."""
        json_formatter = JsonFormatter()
        formatter = SparkJsonFormatter(json_formatter)
        
        # Create a mock traceback that will cause format_exception to raise
        mock_tb = Mock(spec=TracebackType)
        
        with patch('traceback.format_exception', side_effect=Exception("Mock error")):
            result = formatter._format_full(ValueError, ValueError("test"), mock_tb)
            
            # Should fall back to basic format
            assert result == "ValueError: test"

    def test_format_full_no_traceback_line_115(self):
        """Test _format_full with None traceback (line 115)."""
        json_formatter = JsonFormatter()
        formatter = SparkJsonFormatter(json_formatter)
        
        result = formatter._format_full(ValueError, ValueError("test"), None)
        assert result == "ValueError: test"

    def test_format_full_with_valid_traceback_lines_117_118(self):
        """Test _format_full with valid traceback (lines 117-118)."""
        json_formatter = JsonFormatter()
        formatter = SparkJsonFormatter(json_formatter)
        
        # Create a real exception to get valid traceback
        try:
            raise ValueError("test error")
        except ValueError:
            exc_type, exc_value, tb = sys.exc_info()
            
            result = formatter._format_full(exc_type, exc_value, tb)
            
            # Should contain formatted traceback joined with " | "
            assert "ValueError: test error" in result
            assert " | " in result
            # Should contain file and line info
            assert "test_spark_json_formatter_exceptions.py" in result

    def test_sanitize_with_various_inputs(self):
        """Test _sanitize method with various inputs."""
        json_formatter = JsonFormatter()
        formatter = SparkJsonFormatter(json_formatter)
        
        # Test with string containing newlines
        result = formatter._sanitize("line1\nline2\rline3")
        assert result == "line1 line2 line3"
        
        # Test with non-string input
        result = formatter._sanitize(123)
        assert result == "123"
        
        # Test with None
        result = formatter._sanitize(None)
        assert result == "None"
        
        # Test with object
        class TestObj:
            def __str__(self):
                return "test object"
        
        result = formatter._sanitize(TestObj())
        assert result == "test object"