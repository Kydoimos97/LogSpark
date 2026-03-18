"""
Test LoggerConfig functionality.
"""

import logging

import pytest

from logspark._Internal.State.LoggerConfig import LoggerConfig
from logspark.Types.Options import TracebackOptions


class TestLoggerConfig:
    """Test LoggerConfig dataclass"""

    def test_valid_configuration(self):
        """Test LoggerConfig with valid parameters"""
        handler = logging.StreamHandler()
        config = LoggerConfig(
            level=logging.INFO,
            handler=handler,
            traceback_policy=TracebackOptions.COMPACT
        )
        assert config.level == logging.INFO
        assert config.handler == handler
        assert config.traceback_policy == TracebackOptions.COMPACT

    def test_invalid_level_type(self):
        """Test LoggerConfig with invalid level type"""
        handler = logging.StreamHandler()
        with pytest.raises(ValueError, match="level must be a stdlib logging level integer"):
            LoggerConfig(
                level="INFO",  # String instead of int
                handler=handler,
                traceback_policy=TracebackOptions.COMPACT
            )

    def test_invalid_handler_type(self):
        """Test LoggerConfig with invalid handler type"""
        with pytest.raises(ValueError, match="handler must be a stdlib logging.Handlers instance"):
            LoggerConfig(
                level=logging.INFO,
                handler="not_a_handler",  # String instead of Handler
                traceback_policy=TracebackOptions.COMPACT
            )

    def test_invalid_traceback_policy_type(self):
        """Test LoggerConfig with invalid traceback policy type"""
        handler = logging.StreamHandler()
        with pytest.raises(ValueError, match="traceback_policy must be a TracebackOptions enum value"):
            LoggerConfig(
                level=logging.INFO,
                handler=handler,
                traceback_policy="COMPACT"  # String instead of enum
            )

    def test_frozen_dataclass(self):
        """Test that LoggerConfig is frozen (immutable)"""
        handler = logging.StreamHandler()
        config = LoggerConfig(
            level=logging.INFO,
            handler=handler,
            traceback_policy=TracebackOptions.COMPACT
        )
        
        # Should not be able to modify frozen dataclass
        with pytest.raises(AttributeError):
            config.level = logging.DEBUG