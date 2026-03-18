"""
Test LogOverride context manager behavior.

Tests LogOverride scoped level changes and restoration of effective level after context exit.
"""

import logging

import pytest

from logspark import LogOverride


class TestLogOverride:
    """Test LogOverride context manager behavior."""

    def test_scoped_level_changes(self, fresh_logger):
        """Test LogOverride scoped level changes."""
        # Configure logger with INFO level
        fresh_logger.configure()
        original_level = fresh_logger.instance.level
        assert original_level == logging.INFO

        # Use LogOverride to temporarily change to DEBUG
        with LogOverride(level=logging.DEBUG):
            # Inside context, level should be DEBUG
            assert fresh_logger.instance.level == logging.DEBUG

        # After context, level should be restored to INFO
        assert fresh_logger.instance.level == original_level

    def test_restoration_of_effective_level_after_context_exit(self, fresh_logger):
        """Test restoration of effective level after context exit."""
        # Configure with WARNING level
        fresh_logger.configure()
        original_level = fresh_logger.instance.level

        # Nested overrides
        with LogOverride(level=logging.DEBUG):
            assert fresh_logger.instance.level == logging.DEBUG

            with LogOverride(level=logging.ERROR):
                assert fresh_logger.instance.level == logging.ERROR

            # Should restore to DEBUG after inner context
            assert fresh_logger.instance.level == logging.DEBUG

        # Should restore to original WARNING level
        assert fresh_logger.instance.level == original_level

    def test_override_with_unconfigured_logger(self, fresh_logger):
        """Test LogOverride works with unconfigured logger."""
        # Don't configure the logger
        original_level = fresh_logger.instance.level  # This will be default level

        with LogOverride(level=logging.DEBUG):
            # Should change level even for unconfigured logger
            assert fresh_logger.instance.level == logging.DEBUG

        # Should restore original level
        assert fresh_logger.instance.level == original_level

    def test_override_as_decorator(self, fresh_logger):
        """Test LogOverride as decorator."""
        fresh_logger.configure()
        original_level = fresh_logger.instance.level

        @LogOverride(level=logging.DEBUG)
        def test_function():
            # Inside decorated function, level should be DEBUG
            assert fresh_logger.instance.level == logging.DEBUG
            return "success"

        # Call decorated function
        result = test_function()
        assert result == "success"

        # After function, level should be restored
        assert fresh_logger.instance.level == original_level

    def test_override_exception_handling(self, fresh_logger):
        """Test LogOverride restores level even when exception occurs."""
        fresh_logger.configure()
        original_level = fresh_logger.instance.level

        try:
            with LogOverride(level=logging.DEBUG):
                assert fresh_logger.instance.level == logging.DEBUG
                raise ValueError("test exception")
        except ValueError:
            pass

        # Level should be restored even after exception
        assert fresh_logger.instance.level == original_level

    def test_override_with_string_level(self, fresh_logger):
        """Test LogOverride accepts string level names."""
        fresh_logger.configure()
        original_level = fresh_logger.instance.level

        with LogOverride(level="DEBUG"):
            assert fresh_logger.instance.level == logging.DEBUG

        assert fresh_logger.instance.level == original_level

    def test_override_with_invalid_level(self):
        """Test LogOverride raises error for invalid level."""
        with pytest.raises(KeyError):
            LogOverride(level="INVALID_LEVEL")

    def test_override_multiple_instances(self, fresh_logger):
        """Test multiple LogOverride instances work independently."""
        fresh_logger.configure()
        original_level = fresh_logger.instance.level

        override1 = LogOverride(level=logging.DEBUG)
        override2 = LogOverride(level=logging.ERROR)

        # Use first override
        with override1:
            assert fresh_logger.instance.level == logging.DEBUG

        assert fresh_logger.instance.level == original_level

        # Use second override
        with override2:
            assert fresh_logger.instance.level == logging.ERROR

        assert fresh_logger.instance.level == original_level

    def test_override_preserves_frozen_configuration(self, fresh_logger):
        """Test LogOverride doesn't affect frozen configuration."""
        fresh_logger.configure()
        assert fresh_logger.frozen

        with LogOverride(level=logging.DEBUG):
            # Configuration should still be frozen
            assert fresh_logger.frozen
            # But effective level should be changed
            assert fresh_logger.instance.level == logging.DEBUG

        # After override, still frozen with original is_configured
        assert fresh_logger.frozen
        assert fresh_logger.is_configured.level == logging.INFO

    def test_override_with_different_level_types(self, fresh_logger):
        """Test LogOverride works with different level types."""
        fresh_logger.configure()
        original_level = fresh_logger.instance.level

        # Test with integer level
        with LogOverride(level=10):  # DEBUG level
            assert fresh_logger.instance.level == 10

        assert fresh_logger.instance.level == original_level

        # Test with logging constant
        with LogOverride(level=logging.CRITICAL):
            assert fresh_logger.instance.level == logging.CRITICAL

        assert fresh_logger.instance.level == original_level
