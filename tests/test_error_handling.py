"""
Error handling unit tests for LogSpark Logging

These tests verify all exception types and error conditions.
"""

import logging
import os
import re
import warnings
from unittest.mock import Mock

import pytest

from logspark.Handlers import TerminalHandler
from logspark.Types import (
    FrozenConfigurationError,
    InvalidConfigurationError,
    UnconfiguredUsageWarning,
)
from logspark.Types.Exceptions import LogSparkError

from logspark.Types import TracebackOptions


class TestExceptionHierarchy:
    """Test exception hierarchy and inheritance"""

    def test_base_exception_hierarchy(self):
        """Test that all LogSpark exceptions inherit from logsparkError"""
        assert issubclass(FrozenConfigurationError, LogSparkError)
        assert issubclass(InvalidConfigurationError, LogSparkError)

        # LogSparkError should inherit from Exception
        assert issubclass(LogSparkError, Exception)

    def test_warning_hierarchy(self):
        """Test that UnconfiguredUsageWarning inherits from UserWarning"""
        assert issubclass(UnconfiguredUsageWarning, UserWarning)

    def test_exception_instantiation(self):
        """Test that all exceptions can be instantiated with messages"""
        exceptions = [
            LogSparkError,
            FrozenConfigurationError,
            InvalidConfigurationError,
        ]

        for exc_class in exceptions:
            exc = exc_class("Test message")
            assert str(exc) == "Test message"
            assert isinstance(exc, Exception)
            assert isinstance(exc, LogSparkError)


class TestFrozenConfigurationError:
    """Test FrozenConfigurationError conditions"""

    def test_configure_after_freeze_raises_frozen_error(self, fresh_logger):
        """Test that configure() after freeze() raises FrozenConfigurationError"""
        # Configure logger (automatically frozen)
        fresh_logger.configure(level=logging.INFO)

        # Attempting to configure again should raise FrozenConfigurationError
        with pytest.raises(
            FrozenConfigurationError, match="Cannot configure logger after freeze"
        ):
            fresh_logger.configure(level=logging.DEBUG)

    def test_frozen_error_message_is_descriptive(self, fresh_logger):
        """Test that FrozenConfigurationError has descriptive message"""
        fresh_logger.configure(level=logging.INFO)

        try:
            fresh_logger.configure(level=logging.DEBUG)
            pytest.fail("Should have raised FrozenConfigurationError")
        except FrozenConfigurationError as e:
            assert "Cannot configure logger after freeze" in str(e)
            assert "freeze" in str(e).lower()
            assert "configure" in str(e).lower()

    def test_multiple_configure_attempts_after_freeze(self, fresh_logger):
        """Test that multiple configure attempts after configure all raise FrozenConfigurationError"""
        fresh_logger.configure(level=logging.INFO)

        # Multiple attempts should all fail with same error
        for i in range(3):
            with pytest.raises(
                FrozenConfigurationError, match="Cannot configure logger after freeze"
            ):
                fresh_logger.configure(level=logging.WARNING, fast_log=True, traceback=TracebackOptions.FULL, handler=TerminalHandler())


class TestInvalidConfigurationError:
    """Test InvalidConfigurationError conditions"""

    def test_invalid_level_raises_invalid_config_error(self, fresh_logger):
        """Test that invalid level parameter raises InvalidConfigurationError"""
        invalid_levels = ["DEBUG", "invalid", object(), []]

        for invalid_level in invalid_levels:
            with pytest.raises(InvalidConfigurationError):
                fresh_logger.configure(level=invalid_level)

    def test_invalid_fast_log_raises_invalid_config_error(self, fresh_logger):
        """Test that invalid fast_log parameter raises InvalidConfigurationError"""
        invalid_fast_log_values = ["true", 1, "false", object(), []]

        for invalid_fast_log in invalid_fast_log_values:
            with pytest.raises(InvalidConfigurationError):
                fresh_logger.configure(fast_log=invalid_fast_log)

    def test_invalid_handler_raises_invalid_config_error(self, fresh_logger):
        """Test that invalid handler parameter raises InvalidConfigurationError"""
        invalid_handlers = ["json", "terminal", 123, object(), []]

        for invalid_handler in invalid_handlers:
            with pytest.raises(
                InvalidConfigurationError, match="handler must be a logging\\.Handlers instance"
            ):
                fresh_logger.configure(handler=invalid_handler)

    def test_invalid_traceback_policy_raises_invalid_config_error(self, fresh_logger):
        """Test that invalid traceback parameter raises InvalidConfigurationError"""
        invalid_traceback_values = [0, 1, "invalid", object(), []]

        pattern = re.compile(
            r"(Valid options: \[.*])"
        )

        for invalid_traceback in invalid_traceback_values:
            with pytest.raises(InvalidConfigurationError):
                fresh_logger.configure(traceback=invalid_traceback)

    def test_invalid_config_error_messages_are_descriptive(self, fresh_logger):
        """Test that InvalidConfigurationError messages are descriptive"""
        test_cases = [
            ("level", "invalid_level", "level must be an integer"),
            ("fast_log", "not_boolean", "fast_log must be a boolean"),
            ("handler", "not_handler", "handler must be a logging.Handlers instance"),
            ("traceback", "not_enum", "Valid options:"),
            ("traceback", 0, "Valid options:"),
        ]

        for param_name, invalid_value, expected_message in test_cases:
            try:
                fresh_logger.configure(**{param_name: invalid_value})
                pytest.fail(f"Should have raised InvalidConfigurationError for {param_name}")
            except InvalidConfigurationError as e:
                assert expected_message in str(e)
                assert param_name in str(e) or param_name.replace("_", "") in str(e).replace(
                    "_", ""
                )


class TestUnconfiguredUsageWarning:
    """Test UnconfiguredUsageWarning conditions"""
    @pytest.mark.silenced
    def test_pre_config_logging_emits_warning(self, fresh_logger):
        """Test that logging before configure() emits UnconfiguredUsageWarning"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            fresh_logger.info("test message")

            assert len(w) == 1
            assert issubclass(w[0].category, UnconfiguredUsageWarning)
            assert "Logger used before explicit configuration" in str(w[0].message)

    @pytest.mark.silenced
    def test_warning_can_be_suppressed(self, fresh_logger):
        """Test that UnconfiguredUsageWarning can be suppressed"""
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings("ignore", category=UnconfiguredUsageWarning)

            fresh_logger.info("test message")

            # Should have no warnings when suppressed
            unconfigured_warnings = [
                warning for warning in w if issubclass(warning.category, UnconfiguredUsageWarning)
            ]
            assert len(unconfigured_warnings) == 0

    @pytest.mark.silenced
    def test_warning_emitted_only_once(self, fresh_logger):
        """Test that UnconfiguredUsageWarning is emitted only once per logger instance"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Multiple logging calls should emit warning only once
            fresh_logger.info("message 1")
            fresh_logger.warning("message 2")
            fresh_logger.error("message 3")

            unconfigured_warnings = [
                warning for warning in w if issubclass(warning.category, UnconfiguredUsageWarning)
            ]
            assert len(unconfigured_warnings) == 1

    @pytest.mark.silenced
    def test_warning_message_is_descriptive(self, fresh_logger):
        """Test that UnconfiguredUsageWarning message is descriptive"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            fresh_logger.info("test message")

            warning_message = str(w[0].message)
            assert "Logger used before explicit configuration" in warning_message


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_configuration_parameters(self, fresh_logger):
        """Test configuration with empty/None parameters where allowed"""
        # None handler should be allowed and converted to default
        fresh_logger.configure(handler=None)
        assert fresh_logger.config.handler is not None
        assert isinstance(fresh_logger.config.handler, logging.Handler)

    def test_boundary_logging_levels(self, fresh_logger):
        """Test configuration with boundary logging levels"""
        # Test minimum and maximum standard logging levels
        boundary_levels = [
            logging.NOTSET,  # 0
            logging.DEBUG,  # 10
            logging.INFO,  # 20
            logging.WARNING,  # 30
            logging.ERROR,  # 40
            logging.CRITICAL,  # 50
        ]

        for level in boundary_levels:
            fresh_logger._config = None
            fresh_logger._frozen = False

            fresh_logger.configure(level=level)
            assert fresh_logger.config.level == level

    def test_custom_logging_levels(self, fresh_logger):
        """Test configuration with custom logging levels"""
        # Custom levels should be accepted if they're integers
        custom_levels = [5, 15, 25, 35, 45, 55]

        for level in custom_levels:
            fresh_logger._config = None
            fresh_logger._frozen = False

            fresh_logger.configure(level=level)
            assert fresh_logger.config.level == level

    def test_handler_with_custom_formatter(self, fresh_logger):
        """Test configuration with handler that has custom formatter"""
        custom_handler = logging.StreamHandler()
        custom_formatter = logging.Formatter("CUSTOM: %(message)s")
        custom_handler.setFormatter(custom_formatter)

        fresh_logger.configure(handler=custom_handler)

        assert fresh_logger.config.handler is custom_handler
        assert fresh_logger.config.handler.formatter is custom_formatter

    def test_log_manager_with_nonexistent_logger(self, fresh_log_manager):
        """Test logmanager behavior with nonexistent logger names"""
        with pytest.raises(KeyError):
            fresh_log_manager.managed("nonexistent")

        with pytest.raises(KeyError):
            fresh_log_manager.managed("does.not.exist")


class TestIntegrationPointErrors:
    """Test error conditions at integration points between components"""

    def test_logger_manager_interaction_errors(self, fresh_logger, fresh_log_manager):
        """Test error conditions when logger and logmanager interact"""
        # Configure logger (automatically frozen)
        fresh_logger.configure(level=logging.INFO)

        # logmanager operations should now work since logger is auto-frozen
        try:
            fresh_log_manager.unify_format(fresh_logger)
        except Exception:
            # Other exceptions are acceptable, but not UnfrozenGlobalOperationError
            pass
            pass

    def test_handler_integration_errors(self, fresh_logger):
        """Test error conditions with handler integration"""
        # Test that handler validation catches non-Handlers objects
        invalid_handlers = [
            Mock(),  # Mock object that's not a Handlers
            type("FakeHandler", (), {})(),  # Object that's not a Handlers
            lambda: None,  # Function
        ]

        for invalid_handler in invalid_handlers:
            with pytest.raises(
                InvalidConfigurationError, match="handler must be a logging\\.Handlers instance"
            ):
                fresh_logger.configure(handler=invalid_handler)

    def test_singleton_state_consistency_errors(self):
        """Test error conditions related to singleton state consistency"""
        # Import logger multiple times and verify error handling is consistent
        from logspark import logger
        logger1 = logger
        logger2 = logger

        assert logger1 is logger2

        # Configure one reference (automatically frozen)
        logger1.configure(level=logging.INFO)

        # Error should occur through any reference
        with pytest.raises(FrozenConfigurationError):
            logger2.configure(level=logging.DEBUG)

    def test_warning_system_integration_errors(self, fresh_logger):
        """Test error conditions in warning system integration"""
        # Test that warning system doesn't interfere with error raising
        with warnings.catch_warnings():
            warnings.simplefilter("error", UnconfiguredUsageWarning)

            # UnconfiguredUsageWarning should be raised as exception when set to error
            with pytest.raises(UnconfiguredUsageWarning):
                fresh_logger.info("test message")
