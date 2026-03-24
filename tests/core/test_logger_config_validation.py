"""Tests for configure() error conditions and input validation."""

import logging

import pytest

from logspark.Types import FrozenClassException
from logspark.Types.Options import TracebackOptions


class TestLoggerConfigureValidation:
    """Test configure() raises on invalid inputs or state."""

    def test_frozen_raises_frozen_exception(self, fresh_logger):
        """Test that configuring a frozen logger raises FrozenClassException."""
        fresh_logger.configure()
        with pytest.raises(FrozenClassException):
            fresh_logger.configure()

    def test_invalid_level_raises(self, fresh_logger):
        """Test that an invalid level value raises."""
        with pytest.raises((KeyError, ValueError)):
            fresh_logger.configure(level=999999)

    def test_valid_config_passes_validation(self, fresh_logger, test_handler):
        """Test that a valid configuration succeeds without exception."""
        fresh_logger.configure(
            level=logging.INFO,
            handler=test_handler,
            traceback_policy=TracebackOptions.COMPACT,
        )
        assert fresh_logger.is_configured
        assert test_handler in fresh_logger.handlers
        assert fresh_logger.level == logging.INFO