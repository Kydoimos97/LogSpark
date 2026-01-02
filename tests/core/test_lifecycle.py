"""
Test lifecycle behavior: configure → freeze → kill workflow.

Tests the core lifecycle semantics of LogSpark logger including:
- configure() auto-freeze behavior
- frozen configuration immutability
- kill() reset behavior
- unconfigured usage warnings
"""

import logging
import warnings
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from logspark import SparkLogger, logger
from logspark.Types import FrozenConfigurationError, InvalidConfigurationError
from logspark.Types.Exceptions import UnconfiguredUsageWarning


class TestLifecycleWorkflow:
    """Test the configure → freeze → kill workflow."""

    def test_configure_auto_freeze_behavior(self, fresh_logger):
        """Test that configure() automatically freezes configuration."""
        # Initially not frozen
        assert not fresh_logger.is_frozen

        # Configure should auto-freeze
        fresh_logger.configure(level=logging.DEBUG)

        # Should now be frozen
        assert fresh_logger.is_frozen

    def test_frozen_configuration_immutability(self, fresh_logger):
        """Test that frozen configuration cannot be changed."""
        # Configure and freeze
        fresh_logger.configure(level=logging.INFO)
        assert fresh_logger.is_frozen

        # Attempting to configure again should raise error
        with pytest.raises(FrozenConfigurationError, match="Cannot configure logger after freeze"):
            fresh_logger.configure(level=logging.DEBUG)

    def test_configure_ddtrace_filter_duplicate_prevention(self, fresh_logger):
        """Test that DDTrace filter is not duplicated (lines 287-288)."""
        from logspark.Filters.DDTraceCorrelationFilter import DDTraceCorrelationFilter

        # Configure logger first time
        fresh_logger.configure(level=logging.INFO)

        # Count DDTrace filters
        ddtrace_filters = [
            f for f in fresh_logger.instance.filters if isinstance(f, DDTraceCorrelationFilter)
        ]
        assert len(ddtrace_filters) == 1

        # Manually add another DDTrace filter to test duplicate prevention
        fresh_logger.instance.addFilter(DDTraceCorrelationFilter())

        # Verify we now have 2 filters
        ddtrace_filters = [
            f for f in fresh_logger.instance.filters if isinstance(f, DDTraceCorrelationFilter)
        ]
        assert len(ddtrace_filters) == 2

        # Kill and reconfigure - this should reset everything
        fresh_logger.kill()
        fresh_logger.configure(level=logging.INFO)

        # Should only have one DDTrace filter after reconfigure
        ddtrace_filters = [
            f for f in fresh_logger.instance.filters if isinstance(f, DDTraceCorrelationFilter)
        ]
        assert len(ddtrace_filters) == 1

    def test_configure_fast_mode_null_handler(self, fresh_logger):
        """Test that fast mode with no handler uses NullHandler."""
        with patch.dict("os.environ", {"LOGSPARK_MODE": "fast"}):
            fresh_logger.configure(level=logging.INFO)

            # Should use NullHandler for maximum speed in fast mode
            assert len(fresh_logger.instance.handlers) == 1
            assert isinstance(fresh_logger.instance.handlers[0], logging.NullHandler)

    def test_kill_reset_behavior(self, fresh_logger):
        """Test that kill() resets logger to unconfigured state."""
        # Configure and verify frozen state
        fresh_logger.configure(level=logging.INFO)
        assert fresh_logger.is_frozen

        # Kill should reset everything
        fresh_logger.kill()

        # Should be back to unconfigured state
        assert not fresh_logger.is_frozen

        # Should be able to configure again
        fresh_logger.configure(level=logging.DEBUG)
        assert fresh_logger.is_frozen

    def test_unconfigured_usage_warnings(self, fresh_logger):
        """Test that unconfigured usage emits warnings unless silenced."""
        # Using logger before configuration should emit warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            fresh_logger.info("test message")

            # Should have emitted UnconfiguredUsageWarning
            assert len(w) == 1
            assert issubclass(w[0].category, UnconfiguredUsageWarning)
            assert "Logger used before explicit configuration" in str(w[0].message)

    def test_unconfigured_usage_warnings_silenced_mode(self, fresh_logger):
        """Test that unconfigured usage warnings are still emitted in silenced mode."""
        with patch.dict("os.environ", {"LOGSPARK_MODE": "silenced"}):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                fresh_logger.info("test message")

                # Should still emit warnings in silenced mode (silenced only affects output, not warnings)
                unconfigured_warnings = [
                    warning
                    for warning in w
                    if issubclass(warning.category, UnconfiguredUsageWarning)
                ]
                assert len(unconfigured_warnings) == 1

    def test_configure_no_freeze_option(self, fresh_logger):
        """Test that no_freeze=True prevents automatic freezing."""
        # Configure with no_freeze=True
        fresh_logger.configure(level=logging.INFO, no_freeze=True)

        # Should not be frozen
        assert not fresh_logger.is_frozen

        # Should be able to configure again
        fresh_logger.configure(level=logging.DEBUG, no_freeze=True)
        assert not fresh_logger.is_frozen

        # Manual freeze should work
        fresh_logger.freeze()
        assert fresh_logger.is_frozen

    def test_freeze_without_configuration_error(self, fresh_logger):
        """Test that freeze() without configuration raises error."""
        # Attempting to freeze without configuration should raise error
        with pytest.raises(
            InvalidConfigurationError, match="The logger has to be configured by calling configure"
        ):
            fresh_logger.freeze()

    def test_config_property_access_before_configuration(self, fresh_logger):
        """Test that accessing config property before configuration raises error."""
        with pytest.raises(InvalidConfigurationError, match="LogSpark logger not configured"):
            _ = fresh_logger.config

    def test_config_property_access_after_configuration(self, fresh_logger):
        """Test that config property is accessible after configuration."""
        fresh_logger.configure(level=logging.INFO)

        # Should be able to access config
        config = fresh_logger.config
        assert config.level == logging.INFO

    def test_instance_property_creates_stdlib_logger(self, fresh_logger):
        """Test that instance property creates stdlib logger even before configuration."""
        # Accessing instance should create stdlib logger
        stdlib_logger = fresh_logger.instance

        assert isinstance(stdlib_logger, logging.Logger)
        assert stdlib_logger.name == "LogSpark"

    def test_kill_clears_singleton_state(self):
        """Test that kill() properly clears singleton state."""
        # Get initial logger instance
        logger1 = SparkLogger()
        logger1.configure(level=logging.INFO)

        # Kill should reset singleton
        logger1.kill()

        # New instance should be fresh
        logger2 = SparkLogger()
        assert not logger2.is_frozen

        # Should be able to configure new instance
        logger2.configure(level=logging.DEBUG)
        assert logger2.is_frozen

        # Clean up
        logger2.kill()


class TestLifecycleProperties:
    """Property-based tests for lifecycle behavior."""

    def test_property_configure_auto_freeze(self, fresh_logger):
        """

        For any valid configuration parameters, configure() should automatically freeze the logger.

        """
        from hypothesis import given
        from hypothesis import strategies as st

        from logspark.Types import TracebackOptions

        @given(
            level=st.sampled_from([
                logging.DEBUG,
                logging.INFO,
                logging.WARNING,
                logging.ERROR,
                logging.CRITICAL,
            ]),
            traceback_policy=st.sampled_from([
                TracebackOptions.NONE,
                TracebackOptions.COMPACT,
                TracebackOptions.FULL,
            ]),
            no_freeze=st.booleans(),
        )
        def property_test(level, traceback_policy, no_freeze):
            fresh_logger.kill()  # Reset for each iteration

            # Configure with random parameters
            fresh_logger.configure(level=level, traceback=traceback_policy, no_freeze=no_freeze)

            # Should be frozen unless no_freeze=True
            if no_freeze:
                assert not fresh_logger.is_frozen
            else:
                assert fresh_logger.is_frozen

        property_test()

    def test_property_frozen_configuration_immutability(self, fresh_logger):
        """

        For any frozen logger, attempting to configure should raise FrozenConfigurationError.

        """
        from hypothesis import given
        from hypothesis import strategies as st

        @given(
            initial_level=st.sampled_from([logging.DEBUG, logging.INFO, logging.WARNING]),
            second_level=st.sampled_from([logging.ERROR, logging.CRITICAL]),
        )
        def property_test(initial_level, second_level):
            fresh_logger.kill()  # Reset for each iteration

            # Configure and freeze
            fresh_logger.configure(level=initial_level)
            assert fresh_logger.is_frozen

            # Any attempt to reconfigure should fail
            with pytest.raises(FrozenConfigurationError):
                fresh_logger.configure(level=second_level)

        property_test()

    def test_property_unconfigured_usage_warning(self, fresh_logger):
        """

        For any logging call on unconfigured logger, UnconfiguredUsageWarning should be emitted regardless of mode.

        """
        from hypothesis import given
        from hypothesis import strategies as st

        @given(
            log_method=st.sampled_from(["debug", "info", "warning", "error", "critical"]),
            message=st.text(min_size=1, max_size=100),
            silenced=st.booleans(),
        )
        def property_test(log_method, message, silenced):
            fresh_logger.kill()  # Reset for each iteration

            env_patch = {"LOGSPARK_MODE": "silenced"} if silenced else {}

            with patch.dict("os.environ", env_patch, clear=False):
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")

                    # Call the logging method
                    getattr(fresh_logger, log_method)(message)

                    # Check warning behavior - warnings should always be emitted
                    unconfigured_warnings = [
                        warning
                        for warning in w
                        if issubclass(warning.category, UnconfiguredUsageWarning)
                    ]

                    # Warnings should be emitted regardless of silenced mode
                    assert len(unconfigured_warnings) == 1

        property_test()

    def test_property_kill_reset_behavior(self, fresh_logger):
        """

        For any configured logger, kill() should reset to unconfigured state allowing reconfiguration.

        """
        from hypothesis import given
        from hypothesis import strategies as st

        @given(
            initial_level=st.sampled_from([logging.DEBUG, logging.INFO, logging.WARNING]),
            second_level=st.sampled_from([logging.ERROR, logging.CRITICAL]),
        )
        def property_test(initial_level, second_level):
            fresh_logger.kill()  # Reset for each iteration

            # Configure initially
            fresh_logger.configure(level=initial_level)
            assert fresh_logger.is_frozen

            # Kill should reset
            fresh_logger.kill()
            assert not fresh_logger.is_frozen

            # Should be able to reconfigure
            fresh_logger.configure(level=second_level)
            assert fresh_logger.is_frozen
            assert fresh_logger.config.level == second_level

        property_test()


class TestSingletonProperties:
    """Property-based tests for singleton behavior"""

    @given(st.integers(min_value=1, max_value=10))
    def test_singleton_identity_consistency(self, num_imports):
        """Test that logger and logmanager imports return the same singleton instances"""
        from logspark import logger as logger2
        from logspark import spark_log_manager

        logger1 = logger

        from logspark import spark_log_manager as manager2

        manager1 = spark_log_manager

        assert logger1 is logger2
        assert manager1 is manager2
        assert logger1 is logger
        assert manager1 is spark_log_manager

        for _ in range(num_imports):
            temp_logger = logger
            temp_manager = spark_log_manager

            assert temp_logger is logger1
            assert temp_manager is manager1


class TestImportOrderProperties:
    """Property-based tests for import order independence"""

    pass  # Tests removed - incorrect assumptions about automatic logger adoption
