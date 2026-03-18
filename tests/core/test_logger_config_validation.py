"""Tests for LoggerConfig validation errors (lines 27, 30, 33)."""

import logging

import pytest

from logspark._Internal.State.LoggerConfig import LoggerConfig
from logspark.Types.Options import TracebackOptions


class TestLoggerConfigValidation:
    """Test LoggerConfig validation in __post_init__."""

    def test_invalid_level_raises_value_error(self):
        """Test that non-int level raises ValueError (line 27)."""
        handler = logging.StreamHandler()
        
        with pytest.raises(ValueError, match="level must be a stdlib logging level integer"):
            LoggerConfig(
                level="invalid",  # String instead of int
                handler=handler,
                traceback_policy=TracebackOptions.HIDE
            )

    def test_invalid_handler_raises_value_error(self):
        """Test that non-Handler handler raises ValueError (line 30)."""
        with pytest.raises(ValueError, match="handler must be a stdlib logging.Handlers instance"):
            LoggerConfig(
                level=logging.INFO,
                handler="invalid",  # String instead of Handler
                traceback_policy=TracebackOptions.HIDE
            )

    def test_invalid_traceback_policy_raises_value_error(self):
        """Test that non-TracebackOptions traceback_policy raises ValueError (line 33)."""
        handler = logging.StreamHandler()
        
        with pytest.raises(ValueError, match="traceback_policy must be a TracebackOptions enum value"):
            LoggerConfig(
                level=logging.INFO,
                handler=handler,
                traceback_policy="invalid"  # String instead of TracebackOptions
            )

    def test_valid_config_passes_validation(self):
        """Test that valid configuration passes validation."""
        handler = logging.StreamHandler()
        
        # Should not raise any exception
        config = LoggerConfig(
            level=logging.INFO,
            handler=handler,
            traceback_policy=TracebackOptions.COMPACT
        )
        
        assert config.level == logging.INFO
        assert config.handler is handler
        assert config.traceback_policy == TracebackOptions.COMPACT