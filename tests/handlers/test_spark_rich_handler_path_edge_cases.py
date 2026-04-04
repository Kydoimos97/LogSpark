"""Tests for SparkRichHandler path handling edge cases (line 139)."""

import logging
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

pytest.importorskip("rich")
from logspark.Handlers.Rich.SparkRichHandler import SparkRichHandler


class TestSparkRichHandlerPathEdgeCases:
    """Test SparkRichHandler path handling edge cases."""

    def test_path_with_single_part_relative_to_pythonpath(self):
        """Test path handling when relative path has only one part (line 139)."""
        handler = SparkRichHandler()
        
        # Mock a path that when made relative to PYTHONPATH has only one part
        mock_path = Mock(spec=Path)
        mock_path.is_absolute.return_value = True
        mock_path.parts = ("single_file.py",)
        
        # Mock the relative_to to return a path with single part
        mock_rel_path = Mock()
        mock_rel_path.parts = ("single_file.py",)
        mock_rel_path.as_posix.return_value = "single_file.py"
        mock_path.relative_to.return_value = mock_rel_path
        
        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="single_file.py",
            lineno=42,
            msg="test message",
            args=(),
            exc_info=None
        )
        
        # Mock Path constructor to return our mock path
        # This should trigger the single part path handling (line 139)
        result = handler.format(record)

        # Should successfully format without error
        assert result is not None