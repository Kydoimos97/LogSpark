"""Tests for SparkLogger.configure() handler creation and selection."""

import logging

import pytest


class TestSparkLoggerHandlerCreation:
    """Test handler creation logic in SparkLogger.configure()."""

    def test_configure_no_handler_creates_terminal_handler(self, fresh_logger):
        """Test that configure() with no handler creates SparkTerminalHandler."""
        from logspark.Handlers.SparkTerminalHandler import SparkTerminalHandler

        fresh_logger.configure()
        assert len(fresh_logger.handlers) == 1
        assert isinstance(fresh_logger.handlers[0], SparkTerminalHandler)

    def test_configure_explicit_handler_uses_provided(self, fresh_logger, test_handler):
        """Test that configure() uses the explicitly provided handler."""
        fresh_logger.configure(handler=test_handler)
        assert test_handler in fresh_logger.handlers

    def test_configure_adds_exactly_one_handler(self, fresh_logger):
        """Test that configure() results in exactly one handler."""
        fresh_logger.configure()
        assert len(fresh_logger.handlers) == 1

    def test_configure_handler_accessible_via_handlers(self, fresh_logger, test_handler):
        """Test handler is accessible via the handlers property."""
        fresh_logger.configure(handler=test_handler)
        assert fresh_logger.handlers[0] is test_handler