"""
Lifecycle tests for LogSpark Logging

These tests verify the explicit lifecycle: import → configure → freeze → use
"""
import io
import logging
import warnings
from logging import StreamHandler
from unittest.mock import Mock, patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from logspark import logger
from logspark.Hooks.DDTraceCorrelationFilter import DDTraceCorrelationFilter
from logspark.Types import TracebackOptions
from logspark.Types.Exceptions import (
    FrozenConfigurationError,
    InvalidConfigurationError,
    UnconfiguredUsageWarning,
)


class TestLoggerLifecycle:
    """Test logger lifecycle management"""

    def test_configure_sets_config_and_freezes(self, fresh_logger, test_handler):
        """Test that configure() sets configuration and automatically freezes"""
        fresh_logger.configure(level=logging.DEBUG, traceback=TracebackOptions.COMPACT, handler=test_handler)

        assert fresh_logger.is_frozen
        assert fresh_logger._config is not None
        assert fresh_logger.config.level == logging.DEBUG
        assert fresh_logger.config.traceback_policy == TracebackOptions.COMPACT

    def test_configure_after_configure_fails(self, fresh_logger, test_handler):
        """Test that configure() fails after first configure() (since it auto-freezes)"""
        fresh_logger.configure(level=logging.INFO, handler=test_handler)
        assert fresh_logger.is_frozen

        with pytest.raises(FrozenConfigurationError):
            fresh_logger.configure(level=logging.DEBUG, handler=test_handler)

    @pytest.mark.silenced
    def test_pre_config_usage_emits_warning(self, fresh_logger):
        """Test that using logger before configure() emits suppressible warning"""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            fresh_logger.info("test message")

            assert len(w) == 1
            assert issubclass(w[0].category, UnconfiguredUsageWarning)
            assert "Logger used before explicit configuration" in str(w[0].message)

    @pytest.mark.silenced
    def test_pre_config_usage_can_be_suppressed(self, fresh_logger):
        """Test that pre-config warnings can be suppressed"""
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings("ignore", category=UnconfiguredUsageWarning)

            fresh_logger.info("test message")

            assert len(w) == 0

    @pytest.mark.silenced
    def test_kill_method_resets_logger(self, fresh_logger, test_handler):
        """Test that kill() method properly resets the logger"""
        # Configure the logger
        fresh_logger.configure(level=logging.DEBUG, handler=test_handler)
        assert fresh_logger.is_frozen
        assert fresh_logger._config is not None

        # Kill the logger
        fresh_logger.kill()

        # Verify reset state
        assert not fresh_logger.is_frozen
        assert fresh_logger._config is None
        assert fresh_logger._stdlib_logger is None
        assert not fresh_logger._pre_config_setup_done
        assert not fresh_logger._unconfigured_warning_emitted


class TestLoggerConfiguration:
    """Test logger configuration system"""

    def test_default_configuration(self, fresh_logger):
        """Test configure() with default parameters"""
        fresh_logger.configure()

        assert fresh_logger._config is not None
        assert fresh_logger.config.level == logging.INFO
        assert fresh_logger.config.traceback_policy == TracebackOptions.COMPACT
        from logspark.Handlers import TerminalHandler
        assert isinstance(fresh_logger.config.handler, TerminalHandler)

    def test_custom_configuration(self, fresh_logger, test_handler):
        """Test configure() with custom parameters"""
        fresh_logger.configure(level=logging.WARNING, traceback=TracebackOptions.FULL, handler=test_handler)

        config = fresh_logger.config
        assert config.level == logging.WARNING
        assert config.handler is test_handler
        assert config.traceback_policy == TracebackOptions.FULL

    def test_configuration_applied_to_stdlib_logger(self, fresh_logger, test_handler):
        """Test that configuration is applied to underlying stdlib logger"""
        fresh_logger.configure(level=logging.ERROR, handler=test_handler)

        stdlib_logger = fresh_logger.instance
        assert stdlib_logger.level == logging.ERROR
        assert test_handler in stdlib_logger.handlers


class TestLoggerLoggingMethods:
    """Test logger logging methods"""

    def test_logging_methods_work_after_configuration(self):
        """Test that logging methods work after configuration"""
        from logspark import logger
        logger.kill()
        stream = io.StringIO()
        handler = StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.configure(handler=handler)


        logger.info("test info message")
        logger.debug("test debug message")  # Should not appear (level is INFO)
        logger.warning("test warning message")
        logger.error("test error message")
        logger.critical("test critical message")

        output = stream.getvalue()
        assert "INFO: test info message" in output
        assert "test debug message" not in output  # Below threshold
        assert "WARNING: test warning message" in output
        assert "ERROR: test error message" in output
        assert "CRITICAL: test critical message" in output

    @pytest.mark.silenced
    def test_logging_methods_work_before_configuration(self, fresh_logger):
        """Test that logging methods work before configuration (with warnings)"""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("ignore", UnconfiguredUsageWarning)

            # Should not raise errors
            fresh_logger.info("test message")
            fresh_logger.error("test error")

            # Verify stdlib logger was set up
            assert fresh_logger._stdlib_logger is not None


class TestLoggerInstance:
    """Test logger instance property"""

    def test_instance_returns_stdlib_logger(self, configured_logger):
        """Test that instance property returns stdlib Logger"""
        instance = configured_logger.instance
        assert isinstance(instance, logging.Logger)
        assert instance.name == "LogSpark"

    def test_instance_available_before_configuration(self, fresh_logger):
        """Test that instance is available even before configuration"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UnconfiguredUsageWarning)

            instance = fresh_logger.instance
            assert isinstance(instance, logging.Logger)
            assert instance.name == "LogSpark"


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


class TestLifecycleProperties:
    """Property-based tests for lifecycle enforcement"""

    @given(st.integers(min_value=logging.DEBUG, max_value=logging.CRITICAL))
    def test_logger_lifecycle_enforcement(self, log_level):
        """Test that configure() automatically freezes and subsequent configure() calls fail"""
        from logspark import SparkLogger

        test_logger = SparkLogger()
        try:
            test_handler = logging.StreamHandler()
            test_logger.configure(level=log_level, traceback=TracebackOptions.NONE, handler=test_handler)

            assert test_logger._config is not None
            assert test_logger.config.level == log_level
            assert test_logger.is_frozen

            with pytest.raises(FrozenConfigurationError):
                test_logger.configure(level=logging.ERROR, handler=test_handler)

        finally:
            test_logger.kill()

    @pytest.mark.silenced
    @given(st.text(min_size=1, max_size=100))
    def test_pre_configuration_behavior_consistency(self, log_message):
        """Test that logging before configuration emits warnings and provides minimal logging"""
        from logspark import SparkLogger

        test_logger = SparkLogger()
        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                test_logger.info(log_message)
                test_logger.warning(log_message)
                test_logger.error(log_message)

                unconfigured_warnings = [
                    warning for warning in w
                    if issubclass(warning.category, UnconfiguredUsageWarning)
                ]
                assert len(unconfigured_warnings) == 1
                assert "Logger used before explicit configuration" in str(unconfigured_warnings[0].message)

            assert test_logger._stdlib_logger is not None
            assert test_logger._stdlib_logger.name == "LogSpark"
            assert len(test_logger._stdlib_logger.handlers) > 0
            assert test_logger._pre_config_setup_done

        finally:
            test_logger.kill()


class TestConfigurationProperties:
    """Property-based tests for configuration system"""

    @given(
        level=st.sampled_from([logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]),
        traceback_policy=st.sampled_from([TracebackOptions.NONE, TracebackOptions.COMPACT, TracebackOptions.FULL]),
    )
    def test_handler_based_configuration_validation(self, level, traceback_policy):
        """Test that configuration accepts valid parameters and rejects invalid ones"""
        from logspark import SparkLogger
        from logspark.Handlers import JSONHandler, TerminalHandler

        test_logger = SparkLogger()
        try:
            valid_handlers = [logging.StreamHandler(), JSONHandler(), TerminalHandler()]

            for handler in valid_handlers:
                test_logger.kill()  # Reset for each test
                test_logger.configure(level=level, traceback=traceback_policy, handler=handler)

                assert test_logger._config is not None
                assert test_logger.config.level == level
                assert test_logger.config.handler is handler
                assert test_logger.config.traceback_policy == traceback_policy

            # Test invalid parameter types
            test_logger.kill()
            with pytest.raises(InvalidConfigurationError):
                test_logger.configure(level="invalid", traceback=traceback_policy, handler=logging.StreamHandler())

        finally:
            test_logger.kill()

    @given(
        valid_policy=st.sampled_from([TracebackOptions.NONE, TracebackOptions.COMPACT, TracebackOptions.FULL]),
        invalid_policy=st.sampled_from([0, 1, object()]),
    )
    def test_traceback_policy_validation(self, valid_policy, invalid_policy):
        """Test that traceback parameter accepts valid TracebackOptions and rejects invalid values"""
        from logspark import SparkLogger

        test_logger = SparkLogger()
        try:
            test_logger.configure(level=logging.INFO, traceback=valid_policy, handler=logging.StreamHandler())

            assert test_logger._config is not None
            assert test_logger.config.traceback_policy == valid_policy
            assert isinstance(test_logger.config.traceback_policy, TracebackOptions)

            test_logger.kill()

            with pytest.raises(InvalidConfigurationError):
                test_logger.configure(level=logging.INFO, traceback=invalid_policy, handler=logging.StreamHandler())

            assert TracebackOptions.NONE.value is None
            assert TracebackOptions.COMPACT.value == "compact"
            assert TracebackOptions.FULL.value == "full"

        finally:
            test_logger.kill()


class TestLogOverrideProperties:
    """Property-based tests for LogOverride scoped debugging"""

    @given(
        override_level=st.sampled_from([logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]),
        original_level=st.sampled_from([logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]),
    )
    def test_log_override_scope_limitation(self, override_level, original_level):
        """Test that LogOverride affects only logging level and restores previous level"""
        if override_level == original_level:
            return
        
        from logspark import LogOverride, logger

        # Use the global singleton and reset it properly
        test_logger = logger
        test_logger.kill()  # Reset to clean state
        
        try:
            test_handler = logging.StreamHandler()
            test_logger.configure(level=original_level, traceback=TracebackOptions.NONE, handler=test_handler)

            original_config = test_logger.config
            original_frozen_state = test_logger._frozen

            assert test_logger._stdlib_logger.level == original_level

            with LogOverride(level=override_level):
                assert test_logger._stdlib_logger.level == override_level
                assert test_logger.config is original_config
                assert test_logger.config.level == original_level  # Config unchanged
                assert test_logger._frozen == original_frozen_state
                assert test_handler in test_logger._stdlib_logger.handlers

            assert test_logger._stdlib_logger.level == original_level
            assert test_logger.config is original_config
            assert test_logger._frozen == original_frozen_state

            with pytest.raises(InvalidConfigurationError):
                LogOverride(level="DEBUG")

        finally:
            test_logger.kill()


class TestDDTraceIntegration:
    """Test ddtrace correlation field injection"""

    def test_ddtrace_filter_injects_correlation_fields_when_active(self):
        """Test correlation field injection when ddtrace is active"""
        # Create a mock span with trace and span IDs
        mock_span = Mock()
        mock_span.trace_id = 12345
        mock_span.span_id = 67890

        # Create a mock tracer that returns the mock span
        mock_tracer = Mock()
        mock_tracer.current_span.return_value = mock_span

        # Create a test log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )

        # Test the filter with mocked ddtrace - patch the correct import path
        with patch("logspark.Hooks.DDTraceCorrelationFilter._dd_tracer", mock_tracer):
            filter_instance = DDTraceCorrelationFilter()
            result = filter_instance.filter(record)

            # Filter should always return True (allow record through)
            assert result is True

            # Record should have ddtrace correlation fields
            assert hasattr(record, "dd_trace_id")
            assert hasattr(record, "dd_span_id")
            assert record.dd_trace_id == 12345
            assert record.dd_span_id == 67890

    def test_ddtrace_filter_handles_no_active_span(self):
        """Test that filter handles case when no span is active"""
        # Create a mock tracer that returns None (no active span)
        mock_tracer = Mock()
        mock_tracer.current_span.return_value = None

        # Create a test log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )

        # Test the filter with mocked ddtrace (no active span)
        with patch("ddtrace.tracer", mock_tracer):
            filter_instance = DDTraceCorrelationFilter()
            result = filter_instance.filter(record)

            # Filter should always return True (allow record through)
            assert result is True

            # Record should not have ddtrace correlation fields
            assert not hasattr(record, "dd_trace_id")
            assert not hasattr(record, "dd_span_id")

    def test_ddtrace_filter_handles_import_error(self):
        """Test that filter gracefully handles ddtrace not being available"""
        # Create a test log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )

        # Test the filter with ddtrace import error by patching the import
        with patch.dict("sys.modules", {"ddtrace": None}):
            filter_instance = DDTraceCorrelationFilter()
            result = filter_instance.filter(record)

            # Filter should always return True (allow record through)
            assert result is True

            # Record should not have ddtrace correlation fields
            assert not hasattr(record, "dd_trace_id")
            assert not hasattr(record, "dd_span_id")

    def test_ddtrace_filter_handles_other_exceptions(self):
        """Test that filter handles other ddtrace exceptions gracefully"""
        # Create a mock tracer that raises an exception
        mock_tracer = Mock()
        mock_tracer.current_span.side_effect = RuntimeError("ddtrace error")

        # Create a test log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )

        # Test the filter with ddtrace exception
        with patch("ddtrace.tracer", mock_tracer):
            filter_instance = DDTraceCorrelationFilter()
            result = filter_instance.filter(record)

            # Filter should always return True (allow record through)
            assert result is True

            # Record should not have ddtrace correlation fields
            assert not hasattr(record, "dd_trace_id")
            assert not hasattr(record, "dd_span_id")

    @pytest.mark.silenced
    def test_ddtrace_filter_added_to_logger_during_pre_config(self, fresh_logger):
        """Test that ddtrace filter is added during pre-config setup"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UnconfiguredUsageWarning)

            # Trigger pre-config setup
            fresh_logger.info("test message")

            # Verify ddtrace filter was added
            stdlib_logger = fresh_logger._stdlib_logger
            ddtrace_filters = [
                f for f in stdlib_logger.filters if isinstance(f, DDTraceCorrelationFilter)
            ]
            # Allow for at least one filter (may have accumulated from previous tests due to global logger)
            assert len(ddtrace_filters) >= 1, "Should have at least one DDTraceCorrelationFilter"

    @pytest.mark.silenced
    def test_ddtrace_filter_preserved_during_configuration(self, fresh_logger, test_handler):
        """Test that ddtrace filter is preserved during configuration"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UnconfiguredUsageWarning)

            # Trigger pre-config setup first
            fresh_logger.info("test message")

            # Verify filter exists before configuration
            stdlib_logger = fresh_logger._stdlib_logger
            ddtrace_filters_before = [
                f for f in stdlib_logger.filters if isinstance(f, DDTraceCorrelationFilter)
            ]
            assert len(ddtrace_filters_before) == 1

            # Configure the logger
            fresh_logger.configure(level=logging.DEBUG, traceback=TracebackOptions.NONE, handler=test_handler)

            # Verify filter still exists after configuration (should not duplicate)
            ddtrace_filters_after = [
                f for f in stdlib_logger.filters if isinstance(f, DDTraceCorrelationFilter)
            ]
            assert len(ddtrace_filters_after) == 1, (
                "DDTraceCorrelationFilter should be preserved during configuration without duplication"
            )

    def test_ddtrace_never_forces_json_output(self, fresh_logger):
        """Test that ddtrace presence never forces JSON output format"""
        # Mock ddtrace as available
        mock_span = Mock()
        mock_span.trace_id = 12345
        mock_span.span_id = 67890
        mock_tracer = Mock()
        mock_tracer.current_span.return_value = mock_span

        with patch("ddtrace.tracer", mock_tracer):
            # Configure with a StreamHandler (not JSON)
            stream_handler = logging.StreamHandler()
            fresh_logger.configure(level=logging.INFO, traceback=TracebackOptions.NONE, handler=stream_handler)

            # Verify that the handler is still a StreamHandler, not forced to JSON
            assert isinstance(fresh_logger._config.handler, logging.StreamHandler)
            assert fresh_logger._config.handler is stream_handler

            # Verify ddtrace filter is present but doesn't mutate handlers
            stdlib_logger = fresh_logger._stdlib_logger
            assert stream_handler in stdlib_logger.handlers
            ddtrace_filters = [
                f for f in stdlib_logger.filters if isinstance(f, DDTraceCorrelationFilter)
            ]
            assert len(ddtrace_filters) == 1
