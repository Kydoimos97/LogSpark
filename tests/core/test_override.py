"""
Test TempLogLevel context manager behavior.

Tests TempLogLevel scoped level changes and restoration of effective level after context exit.
"""

import logging

import pytest

from logspark import TempLogLevel


class TestTempLogLevel:
    """Test TempLogLevel context manager behavior."""

    def test_scoped_level_changes(self, fresh_logger):
        """Test TempLogLevel scoped level changes."""
        fresh_logger.configure()
        original_level = fresh_logger.level
        assert original_level == logging.INFO

        with TempLogLevel(level=logging.DEBUG):
            assert fresh_logger.level == logging.DEBUG

        assert fresh_logger.level == original_level

    def test_restoration_of_effective_level_after_context_exit(self, fresh_logger):
        """Test restoration of effective level after context exit."""
        fresh_logger.configure()
        original_level = fresh_logger.level

        with TempLogLevel(level=logging.DEBUG):
            assert fresh_logger.level == logging.DEBUG

            with TempLogLevel(level=logging.ERROR):
                assert fresh_logger.level == logging.ERROR

            assert fresh_logger.level == logging.DEBUG

        assert fresh_logger.level == original_level

    def test_override_with_unconfigured_logger(self, fresh_logger):
        """Test TempLogLevel works with unconfigured logger."""
        original_level = fresh_logger.level

        with TempLogLevel(level=logging.DEBUG):
            assert fresh_logger.level == logging.DEBUG

        assert fresh_logger.level == original_level

    def test_override_as_decorator(self, fresh_logger):
        """Test TempLogLevel as decorator."""
        fresh_logger.configure()
        original_level = fresh_logger.level

        @TempLogLevel(level=logging.DEBUG)
        def test_function():
            assert fresh_logger.level == logging.DEBUG
            return "success"

        result = test_function()
        assert result == "success"
        assert fresh_logger.level == original_level

    def test_override_exception_handling(self, fresh_logger):
        """Test TempLogLevel restores level even when exception occurs."""
        fresh_logger.configure()
        original_level = fresh_logger.level

        try:
            with TempLogLevel(level=logging.DEBUG):
                assert fresh_logger.level == logging.DEBUG
                raise ValueError("test exception")
        except ValueError:
            pass

        assert fresh_logger.level == original_level

    def test_override_with_string_level(self, fresh_logger):
        """Test TempLogLevel accepts string level names."""
        fresh_logger.configure()
        original_level = fresh_logger.level

        with TempLogLevel(level="DEBUG"):
            assert fresh_logger.level == logging.DEBUG

        assert fresh_logger.level == original_level

    def test_override_with_invalid_level(self):
        """Test TempLogLevel raises error for invalid level."""
        with pytest.raises(KeyError):
            TempLogLevel(level="INVALID_LEVEL")

    def test_override_multiple_instances(self, fresh_logger):
        """Test multiple TempLogLevel instances work independently."""
        fresh_logger.configure()
        original_level = fresh_logger.level

        override1 = TempLogLevel(level=logging.DEBUG)
        override2 = TempLogLevel(level=logging.ERROR)

        with override1:
            assert fresh_logger.level == logging.DEBUG
        assert fresh_logger.level == original_level

        with override2:
            assert fresh_logger.level == logging.ERROR
        assert fresh_logger.level == original_level

    def test_override_preserves_frozen_state(self, fresh_logger):
        """Test TempLogLevel does not unfreeze the logger."""
        fresh_logger.configure()
        assert fresh_logger.frozen

        with TempLogLevel(level=logging.DEBUG):
            assert fresh_logger.frozen
            assert fresh_logger.level == logging.DEBUG

        assert fresh_logger.frozen

    def test_override_with_integer_level(self, fresh_logger):
        """Test TempLogLevel works with raw integer levels."""
        fresh_logger.configure()
        original_level = fresh_logger.level

        with TempLogLevel(level=10):
            assert fresh_logger.level == 10

        assert fresh_logger.level == original_level
