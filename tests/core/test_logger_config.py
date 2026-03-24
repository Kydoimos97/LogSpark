"""
Test logger configure state.

Tests that configure() correctly establishes logger state including handler
attachment, level, and freeze behavior.
"""

import logging

import pytest

from logspark.Types import FrozenClassException
from logspark.Types.Options import TracebackOptions


class TestLoggerConfigureState:
    """Test logger state after configure()."""

    def test_configure_sets_is_configured(self, fresh_logger):
        """Test that configure() sets is_configured to True."""
        assert not fresh_logger.is_configured
        fresh_logger.configure()
        assert fresh_logger.is_configured

    def test_configure_sets_frozen(self, fresh_logger):
        """Test that configure() freezes the logger by default."""
        assert not fresh_logger.frozen
        fresh_logger.configure()
        assert fresh_logger.frozen

    def test_configure_attaches_handler(self, fresh_logger, test_handler):
        """Test that configure() attaches the provided handler."""
        fresh_logger.configure(handler=test_handler)
        assert test_handler in fresh_logger.handlers

    def test_configure_sets_level(self, fresh_logger):
        """Test that configure() sets the log level."""
        fresh_logger.configure(level=logging.DEBUG)
        assert fresh_logger.level == logging.DEBUG

    def test_configure_no_freeze_defers_freeze(self, fresh_logger):
        """Test that no_freeze=True allows further configuration."""
        fresh_logger.configure(no_freeze=True)
        assert fresh_logger.is_configured
        assert not fresh_logger.frozen

    def test_frozen_logger_rejects_further_handlers(self, fresh_logger):
        """Test that a frozen logger rejects addHandler calls."""
        fresh_logger.configure()
        assert fresh_logger.frozen
        with pytest.raises(FrozenClassException):
            fresh_logger.addHandler(logging.NullHandler())