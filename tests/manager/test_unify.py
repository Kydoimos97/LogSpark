"""
Test unify behavior for LogSpark manager.

Tests handler replacement, level mutation, propagation control,
and error conditions for unify operations.
"""

import logging

import pytest
from hypothesis import given
from hypothesis import strategies as st

from logspark import spark_log_manager
from logspark.Types import InvalidConfigurationError, UnfrozenGlobalOperationError


class TestUnify:
    """Test unify behavior for handler replacement and configuration."""

    def test_unify_handler_replacement(self, fresh_log_manager, test_handler):
        """Test that unify() replaces handlers on managed loggers."""
        # Create and adopt loggers
        logger1 = logging.getLogger("test.unify.1")
        logger2 = logging.getLogger("test.unify.2")

        # Add initial handlers
        initial_handler1 = logging.StreamHandler()
        initial_handler2 = logging.StreamHandler()
        logger1.addHandler(initial_handler1)
        logger2.addHandler(initial_handler2)

        fresh_log_manager.adopt(logger1)
        fresh_log_manager.adopt(logger2)

        # Unify with new handler
        fresh_log_manager.unify(handler=test_handler)

        # Verify handlers were replaced
        assert len(logger1.handlers) == 1
        assert len(logger2.handlers) == 1
        assert logger1.handlers[0] is test_handler
        assert logger2.handlers[0] is test_handler

        # Verify old handlers were removed
        assert initial_handler1 not in logger1.handlers
        assert initial_handler2 not in logger2.handlers

    def test_unify_level_mutation(self, fresh_log_manager):
        """Test that unify() sets levels on managed loggers."""
        # Create and adopt loggers with different initial levels
        logger1 = logging.getLogger("test.level.1")
        logger2 = logging.getLogger("test.level.2")
        logger1.setLevel(logging.DEBUG)
        logger2.setLevel(logging.ERROR)

        fresh_log_manager.adopt(logger1)
        fresh_log_manager.adopt(logger2)

        # Unify with new level
        fresh_log_manager.unify(level=logging.WARNING)

        # Verify levels were set
        assert logger1.level == logging.WARNING
        assert logger2.level == logging.WARNING

    def test_unify_propagation_control(self, fresh_log_manager):
        """Test that unify() controls propagation on managed loggers."""
        # Create and adopt loggers with different propagation settings
        logger1 = logging.getLogger("test.prop.1")
        logger2 = logging.getLogger("test.prop.2")
        logger1.propagate = True
        logger2.propagate = False

        fresh_log_manager.adopt(logger1)
        fresh_log_manager.adopt(logger2)

        # Unify with propagation disabled
        fresh_log_manager.unify(propagate=False)

        # Verify propagation was set
        assert logger1.propagate is False
        assert logger2.propagate is False

        # Test setting propagation to True
        fresh_log_manager.unify(propagate=True)
        assert logger1.propagate is True
        assert logger2.propagate is True

    def test_unify_combined_configuration(self, fresh_log_manager, test_handler):
        """Test unify() with handler, level, and propagation together."""
        # Create and adopt logger
        logger = logging.getLogger("test.combined")
        logger.setLevel(logging.DEBUG)
        logger.propagate = True
        logger.addHandler(logging.StreamHandler())

        fresh_log_manager.adopt(logger)

        # Unify with all parameters
        fresh_log_manager.unify(handler=test_handler, level=logging.ERROR, propagate=False)

        # Verify all settings were applied
        assert len(logger.handlers) == 1
        assert logger.handlers[0] is test_handler
        assert logger.level == logging.ERROR
        assert logger.propagate is False

    def test_unify_use_spark_handler_not_configured(self, fresh_log_manager):
        """Test that unify() with use_spark_handler=True raises error when LogSpark not is_configured."""
        # Create and adopt logger
        logger = logging.getLogger("test.spark.error")
        fresh_log_manager.adopt(logger)

        # Ensure LogSpark is not is_configured
        from logspark import logger as spark_logger

        spark_logger.kill()

        # Verify error is raised
        with pytest.raises(InvalidConfigurationError, match="LogSpark logger not is_configured"):
            fresh_log_manager.unify(use_spark_handler=True)

    def test_unify_use_spark_handler_not_frozen(self, fresh_log_manager, test_handler):
        """Test that unify() with use_spark_handler=True raises error when LogSpark not frozen."""
        # Create and adopt logger
        logger = logging.getLogger("test.spark.unfrozen")
        fresh_log_manager.adopt(logger)

        # Configure LogSpark but don't freeze using no_freeze=True
        from logspark import logger as spark_logger
        from logspark.Types.Options import TracebackOptions

        spark_logger.kill()
        spark_logger.configure(
            level=logging.INFO,
            traceback=TracebackOptions.HIDE,
            handler=test_handler,
            no_freeze=True,
        )

        # Verify error is raised
        with pytest.raises(
            UnfrozenGlobalOperationError, match="LogSpark logger needs to be frozen"
        ):
            fresh_log_manager.unify(use_spark_handler=True)

    def test_unify_use_spark_handler_success(self, fresh_log_manager, test_handler):
        """Test successful unify() with use_spark_handler=True."""
        # Create and adopt logger
        logger = logging.getLogger("test.spark.success")
        fresh_log_manager.adopt(logger)

        # Configure and freeze LogSpark
        from logspark import logger as spark_logger
        from logspark.Types.Options import TracebackOptions

        spark_logger.kill()
        spark_logger.configure(
            level=logging.INFO, traceback=TracebackOptions.HIDE, handler=test_handler
        )
        # configure() auto-freezes

        # Unify using LogSpark handler
        fresh_log_manager.unify(use_spark_handler=True)

        # Verify handler was copied
        assert len(logger.handlers) == 1
        assert logger.handlers[0] is test_handler

    def test_unify_invalid_handler_type(self, fresh_log_manager):
        """Test that unify() raises ValueError for invalid handler type."""
        # Create and adopt logger
        logger = logging.getLogger("test.invalid.handler")
        fresh_log_manager.adopt(logger)

        # Verify error is raised for non-handler object
        with pytest.raises(ValueError, match="Handler must be a logging.Handler instance"):
            fresh_log_manager.unify(handler="not a handler")

    def test_unify_level_validation(self, fresh_log_manager):
        """Test that unify() validates log levels."""
        # Create and adopt logger
        logger = logging.getLogger("test.level.validation")
        fresh_log_manager.adopt(logger)

        # Test valid string level
        fresh_log_manager.unify(level="INFO")
        assert logger.level == logging.INFO

        # Test valid integer level
        fresh_log_manager.unify(level=logging.DEBUG)
        assert logger.level == logging.DEBUG

    def test_unify_preserves_unspecified_settings(self, fresh_log_manager, test_handler):
        """Test that unify() preserves settings not explicitly specified."""
        # Create and adopt logger with specific settings
        logger = logging.getLogger("test.preserve")
        logger.setLevel(logging.WARNING)
        logger.propagate = False
        initial_handler = logging.StreamHandler()
        logger.addHandler(initial_handler)

        fresh_log_manager.adopt(logger)

        # Unify with only handler specified
        fresh_log_manager.unify(handler=test_handler)

        # Verify handler was replaced but other settings preserved
        assert len(logger.handlers) == 1
        assert logger.handlers[0] is test_handler
        assert logger.level == logging.WARNING  # Preserved
        assert logger.propagate is False  # Preserved

    def test_unify_no_managed_loggers(self, fresh_log_manager):
        """Test that unify() works with no managed loggers."""
        # Ensure no loggers are managed
        assert len(fresh_log_manager.managed_names) == 0

        # Unify should not raise error
        fresh_log_manager.unify(level=logging.INFO)

        # Still no managed loggers
        assert len(fresh_log_manager.managed_names) == 0


class TestUnifyProperties:
    """Property-based tests for unify behavior."""

    @given(
        st.sampled_from([
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ])
    )
    def test_unify_configuration_application_property(self, level_value):
        """
        For any unify() call with frozen configuration, configuration should be
        applied to all managed loggers.
        """
        # Get fresh manager instance
        spark_log_manager.release_all()

        # Create test handler
        import io

        test_stream = io.StringIO()
        test_handler = logging.StreamHandler(test_stream)

        # Use unique test ID to avoid conflicts
        import uuid

        test_id = str(uuid.uuid4())[:8]

        # Create and adopt multiple loggers
        loggers = []
        for i in range(3):
            logger = logging.getLogger(f"test.unify.prop.{test_id}.{i}")
            logger.setLevel(logging.DEBUG)  # Different from target
            logger.propagate = True  # Different from target
            logger.addHandler(logging.StreamHandler())  # Will be replaced
            loggers.append(logger)
            spark_log_manager.adopt(logger)

        # Apply unify configuration
        target_level = level_value
        target_propagate = False

        spark_log_manager.unify(
            handler=test_handler, level=target_level, propagate=target_propagate
        )

        # Verify configuration was applied to all managed loggers
        for logger in loggers:
            assert len(logger.handlers) == 1, f"Logger {logger.name} should have exactly 1 handler"
            assert logger.handlers[0] is test_handler, (
                f"Logger {logger.name} should have the test handler"
            )
            assert logger.level == target_level, (
                f"Logger {logger.name} should have level {target_level}"
            )
            assert logger.propagate == target_propagate, (
                f"Logger {logger.name} should have propagate={target_propagate}"
            )
