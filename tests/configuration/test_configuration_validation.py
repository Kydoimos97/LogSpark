"""
Tests for configure() parameter handling.

Tests the configure() method validation, parameter acceptance, and error conditions.
"""

import logging

import pytest

from logspark.Types import FrozenClassException
from logspark.Types.Options import TracebackOptions, PathResolutionSetting


class TestConfigureParameters:
    """Test configure() method accepts valid parameters."""

    def test_configure_default_parameters(self, fresh_logger):
        """Test configure() with default parameters succeeds."""
        fresh_logger.configure()
        assert fresh_logger.is_configured
        assert fresh_logger.frozen

    def test_configure_with_explicit_level_int(self, fresh_logger):
        """Test configure() accepts integer log level."""
        fresh_logger.configure(level=logging.DEBUG)
        assert fresh_logger.level == logging.DEBUG

    def test_configure_with_explicit_level_string(self, fresh_logger):
        """Test configure() accepts string log level."""
        fresh_logger.configure(level="WARNING")
        assert fresh_logger.level == logging.WARNING

    def test_configure_with_explicit_handler(self, fresh_logger, test_handler):
        """Test configure() accepts explicit handler."""
        fresh_logger.configure(handler=test_handler)
        assert fresh_logger.is_configured
        assert test_handler in fresh_logger.handlers

    def test_configure_with_traceback_policy_hide(self, fresh_logger):
        """Test configure() accepts HIDE traceback policy."""
        fresh_logger.configure(traceback_policy=TracebackOptions.HIDE)
        assert fresh_logger.is_configured

    def test_configure_with_traceback_policy_full(self, fresh_logger):
        """Test configure() accepts FULL traceback policy."""
        fresh_logger.configure(traceback_policy=TracebackOptions.FULL)
        assert fresh_logger.is_configured

    def test_configure_with_path_resolution_absolute(self, fresh_logger):
        """Test configure() accepts ABSOLUTE path resolution."""
        fresh_logger.configure(path_resolution=PathResolutionSetting.ABSOLUTE)
        assert fresh_logger.is_configured

    def test_configure_with_no_freeze_true(self, fresh_logger):
        """Test configure() with no_freeze=True does not freeze the logger."""
        fresh_logger.configure(no_freeze=True)
        assert fresh_logger.is_configured
        assert not fresh_logger.frozen

    def test_configure_with_no_freeze_false_freezes(self, fresh_logger):
        """Test configure() with no_freeze=False (default) freezes the logger."""
        fresh_logger.configure(no_freeze=False)
        assert fresh_logger.frozen


class TestConfigureErrorConditions:
    """Test configure() raises on invalid state or parameters."""

    def test_configure_frozen_logger_raises(self, fresh_logger):
        """Test configuring a frozen logger raises FrozenClassException."""
        fresh_logger.configure()
        assert fresh_logger.frozen
        with pytest.raises(FrozenClassException):
            fresh_logger.configure()

    def test_configure_invalid_level_raises(self, fresh_logger):
        """Test configure() with invalid level raises."""
        with pytest.raises((KeyError, ValueError)):
            fresh_logger.configure(level=999999)


class TestConfigureHandlerPrecedence:
    """Test configure() handler selection."""

    def test_explicit_handler_takes_priority(self, fresh_logger, test_handler):
        """Test that an explicit handler is used when provided."""
        fresh_logger.configure(handler=test_handler)
        assert test_handler in fresh_logger.handlers

    def test_no_handler_creates_terminal_handler(self, fresh_logger):
        """Test that no handler argument results in SparkTerminalHandler."""
        from logspark.Handlers.SparkTerminalHandler import SparkTerminalHandler

        fresh_logger.configure()
        assert len(fresh_logger.handlers) == 1
        assert isinstance(fresh_logger.handlers[0], SparkTerminalHandler)
