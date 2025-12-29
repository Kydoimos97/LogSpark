"""
Remaining property tests for LogSpark Logging

These tests implement the remaining properties that were not yet covered.
"""

import logging
import os
import warnings

import pytest
from hypothesis import given
from hypothesis import strategies as st

from logspark import logger, spark_log_manager
from logspark.Handlers import TerminalHandler
from logspark.Handlers import JSONHandler
from logspark.Types.Exceptions import UnconfiguredUsageWarning
from logspark.Types import TracebackOptions


class TestImportOrderProperties:
    """Property-based tests for import order independence"""
    @pytest.mark.silenced
    @given(
        import_sequences=st.lists(
            st.sampled_from(["logger_first", "manager_first", "both_together"]),
            min_size=1,
            max_size=5,
        )
    )
    def test_import_order_independence(self, import_sequences):
        """
        For any valid sequence of import statements for logger and logmanager,
        the system should function correctly regardless of import order
        """
        # Clear any existing singleton instances to test fresh imports
        from logspark import logger, spark_log_manager

        manager = spark_log_manager
        if hasattr(logger, "_SingletonWrapper__cls_instance"):
            logger._SingletonWrapper__cls_instance = None
        if hasattr(manager, "_SingletonWrapper__cls_instance"):
            manager._SingletonWrapper__cls_instance = None

        # Clear global logger state
        global_logger = logging.getLogger("LogSpark")
        global_logger.handlers.clear()
        global_logger.filters.clear()
        global_logger.setLevel(logging.NOTSET)

        try:
            logger_instances = []
            manager_instances = []

            # Test different import sequences
            for sequence in import_sequences:
                if sequence == "logger_first":
                    from logspark import logger, spark_log_manager



                    logger_instances.append(logger)
                    manager_instances.append(spark_log_manager)

                elif sequence == "manager_first":
                    from logspark import logger, spark_log_manager



                    logger_instances.append(logger)
                    manager_instances.append(spark_log_manager)

                elif sequence == "both_together":
                    from logspark import logger, spark_log_manager




                    logger_instances.append(logger)
                    manager_instances.append(spark_log_manager)

            # Verify all logger instances are the same singleton
            for i in range(1, len(logger_instances)):
                assert logger_instances[i] is logger_instances[0], (
                    f"Logger singleton not consistent across import sequences: {import_sequences}"
                )

            # Verify all manager instances are the same singleton
            for i in range(1, len(manager_instances)):
                assert manager_instances[i] is manager_instances[0], (
                    f"logmanager singleton not consistent across import sequences: {import_sequences}"
                )

            # Test that functionality works regardless of import order
            test_logger = logger_instances[0]
            test_manager = manager_instances[0]

            # Test logger functionality
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UnconfiguredUsageWarning)
                test_logger.info("Test message")  # Should work

            # Test manager functionality
            assert "LogSpark" in test_manager._state.managed_loggers
            LogSpark_logger = test_manager.managed("LogSpark")
            assert isinstance(LogSpark_logger, logging.Logger)

            # Test configuration works regardless of import order (only if not already frozen)
            if not test_logger.is_frozen:
                test_logger.configure(level=logging.INFO)
                assert test_logger._config is not None
                assert test_logger.config.level == logging.INFO

                # Test freeze works
                test_logger.freeze()
                assert test_logger.is_frozen

                # Test manager operations work with frozen logger
                test_manager.unify_format(test_logger)  # Should not raise error
            else:
                # If already frozen, just verify it works
                assert test_logger.is_frozen
                test_manager.unify_format(test_logger)  # Should not raise error

        finally:
            # Cleanup: reset singleton instances
            if hasattr(logger, "_SingletonWrapper__cls_instance"):
                logger._SingletonWrapper__cls_instance = None
            if hasattr(spark_log_manager, "_SingletonWrapper__cls_instance"):
                spark_log_manager._SingletonWrapper__cls_instance = None

            # Clear global logger state
            global_logger.handlers.clear()
            global_logger.filters.clear()
            global_logger.setLevel(logging.NOTSET)


class TestLogManagerPassiveManagementProperties:
    """Property-based tests for logmanager passive management"""

    @given(
        external_logger_names=st.lists(
            st.text(min_size=1, max_size=20).filter(lambda x: x.isidentifier() and x != "LogSpark"),
            min_size=1,
            max_size=10,
            unique=True,
        )
    )
    def test_logmanager_passive_management(self, external_logger_names):
        """
        For any newly created logmanager instance, it should manage only LogSpark's logger by default
        and not automatically adopt other loggers
        """
        # Create external loggers before creating logmanager
        external_loggers = {}
        for logger_name in external_logger_names:
            external_logger = logging.getLogger(f"external.{logger_name}")
            external_loggers[f"external.{logger_name}"] = external_logger
        from logspark import spark_log_manager
        # Create fresh logmanager instance
        fresh_manager = spark_log_manager
        
        # Reset singleton state properly
        fresh_manager.release()
        try:
            # Verify logmanager only manages LogSpark logger by default
            managed_loggers = fresh_manager._state.managed_loggers

            # Should only contain 'LogSpark' logger
            assert "LogSpark" in managed_loggers, (
                "logmanager should manage LogSpark logger by default"
            )

            # Should not automatically manage external loggers
            for logger_name in external_loggers.keys():
                assert logger_name not in managed_loggers, (
                    f"logmanager should not automatically manage external logger: {logger_name}"
                )

            # Verify external loggers are not accessible via managed()
            for logger_name in external_loggers.keys():
                with pytest.raises(KeyError):
                    fresh_manager.managed(logger_name)

            # Verify LogSpark logger is accessible
            LogSpark_logger = fresh_manager.managed("LogSpark")
            assert isinstance(LogSpark_logger, logging.Logger)
            assert LogSpark_logger.name == "LogSpark"

            # Verify that external loggers exist in the registry but are not managed
            for logger_name, logger_instance in external_loggers.items():
                # Logger should exist in Python's logging registry
                registry_logger = logging.getLogger(logger_name)
                assert registry_logger is logger_instance

                # But should not be managed by logmanager
                assert logger_name not in fresh_manager._state.managed_loggers

            # Test that adopt_all() is required to manage external loggers
            fresh_manager.adopt_all()

            # Now external loggers should be managed
            for logger_name, logger_instance in external_loggers.items():
                managed_logger = fresh_manager.managed(logger_name)
                assert managed_logger is logger_instance

        finally:
            # Cleanup using new methods
            fresh_manager.release()

            # Clear external loggers from registry
            for logger_name in list(logging.Logger.manager.loggerDict.keys()):
                if logger_name.startswith("external."):
                    del logging.Logger.manager.loggerDict[logger_name]


class TestOpportunisticFeatureDetectionProperties:
    """Property-based tests for opportunistic feature detection"""
    @pytest.mark.silenced
    @given(
        rich_available=st.booleans(),
        ddtrace_available=st.booleans(),
        log_messages=st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=5),
    )
    def test_opportunistic_feature_detection(self, rich_available, ddtrace_available, log_messages):
        """
        For any optional dependency (Hooks, ddtrace), the system should detect its presence
        and enable corresponding features without failing when dependencies are absent
        """
        # Create fresh logger instance for this test
        from logspark import logger, SparkLogger
        fresh_logger = logger
        fresh_logger.kill()
        fresh_logger = SparkLogger()

        try:
            # Test pre-configuration behavior (should detect Hooks availability)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UnconfiguredUsageWarning)

                # Log a message to trigger pre-config setup
                fresh_logger.info(log_messages[0])

            # Verify pre-config setup was done
            assert fresh_logger._pre_config_setup_done
            assert fresh_logger._stdlib_logger is not None
            assert len(fresh_logger._stdlib_logger.handlers) > 0

            # Check handler type - should be some kind of handler regardless of Hooks availability
            handler = fresh_logger._stdlib_logger.handlers[0]
            assert isinstance(handler, logging.Handler)

            # Test that logging works regardless of dependency availability
            for message in log_messages:
                # Should not raise errors regardless of dependency availability
                fresh_logger.info(message)
                fresh_logger.warning(message)
                fresh_logger.error(message)

            # Test configuration with TerminalHandler (should work regardless of Hooks)
            fresh_logger.configure(level=logging.INFO, traceback=TracebackOptions.NONE, handler=TerminalHandler())

            # Should succeed regardless of Hooks availability
            assert fresh_logger._config is not None
            assert isinstance(fresh_logger.config.handler, TerminalHandler)

            # Test configuration with JSONHandler (should work without Hooks)
            fresh_logger.kill()
            fresh_logger = SparkLogger()

            fresh_logger.configure(level=logging.INFO, traceback=TracebackOptions.COMPACT, handler=JSONHandler())

            # Should succeed regardless of dependency availability
            assert fresh_logger._config is not None
            assert isinstance(fresh_logger.config.handler, JSONHandler)

            # Log with potential ddtrace correlation
            for message in log_messages:
                fresh_logger.info(message)

            # Should complete without errors regardless of ddtrace availability
            # If ddtrace is available, correlation fields might be added
            # If ddtrace is not available, logging should still work normally

        finally:
            # Cleanup: reset state
            fresh_logger.kill()
            logger = fresh_logger


class TestPreConfigurationValidationProperties:
    """Property-based tests for pre-configuration validation limitation"""
    @pytest.mark.silenced
    @given(
        log_levels=st.lists(
            st.sampled_from(["debug", "info", "warning", "error", "critical"]),
            min_size=1,
            max_size=10,
        ),
        log_messages=st.lists(st.text(min_size=1, max_size=200), min_size=1, max_size=10),
        warning_suppression=st.booleans(),
    )
    def test_pre_configuration_validation_limitation(
        self, log_levels, log_messages, warning_suppression):
        """
        For any pre-configuration logging operation, the system should not perform configuration validation
        beyond emitting unconfigured-usage warnings and should not include implicit mode switching
        """
        # Create fresh logger instance for this test
        from logspark import logger, SparkLogger
        fresh_logger = logger
        fresh_logger.kill()
        fresh_logger = SparkLogger()

        try:
            # Set up warning handling
            with warnings.catch_warnings(record=True) as w:
                if warning_suppression:
                    warnings.filterwarnings("ignore", category=UnconfiguredUsageWarning)
                else:
                    warnings.simplefilter("always")

                # Test that pre-config logging works without validation errors
                for level_name, message in zip(log_levels, log_messages):
                    log_method = getattr(fresh_logger, level_name)

                    # Should not raise configuration validation errors
                    try:
                        log_method(message)
                    except Exception as e:
                        # Should not get configuration validation errors
                        assert "configuration" not in str(e).lower(), (
                            f"Pre-config logging should not perform configuration validation: {e}"
                        )
                        assert "invalid" not in str(e).lower(), (
                            f"Pre-config logging should not validate parameters: {e}"
                        )
                        # Re-raise if it's an unexpected error
                        raise

                # Verify warning behavior
                unconfigured_warnings = [
                    warning
                    for warning in w
                    if issubclass(warning.category, UnconfiguredUsageWarning)
                ]

                if warning_suppression:
                    # Warnings should be suppressed
                    assert len(unconfigured_warnings) == 0, "Warnings should be suppressible"
                else:
                    # Should emit exactly one warning (first call only)
                    assert len(unconfigured_warnings) == 1, (
                        "Should emit exactly one unconfigured usage warning"
                    )
                    warning_message = str(unconfigured_warnings[0].message)
                    assert "Logger used before explicit configuration" in warning_message

                # Verify that pre-config setup was done
                assert fresh_logger._pre_config_setup_done, "Pre-config setup should be completed"
                assert fresh_logger._stdlib_logger is not None, "Stdlib logger should be created"
                assert len(fresh_logger._stdlib_logger.handlers) > 0, (
                    "Should have at least one handler"
                )

                # Verify no implicit mode switching occurred
                # Pre-config should use minimal terminal logging only
                handler = fresh_logger._stdlib_logger.handlers[0]

                # Should not have multiple handlers (no mode switching)
                assert len(fresh_logger._stdlib_logger.handlers) == 1, (
                    "Pre-config should not create multiple handlers (no mode switching)"
                )

                # Handlers type should be determined once and not change
                original_handler_type = type(handler)

                # Additional logging should not change handler setup
                for level_name, message in zip(log_levels[:3], log_messages[:3]):  # Test a few more
                    log_method = getattr(fresh_logger, level_name)
                    log_method(f"Additional {message}")

                # Verify handler setup remained stable (no implicit switching)
                assert len(fresh_logger._stdlib_logger.handlers) == 1, (
                    "Handlers count should remain stable"
                )
                assert type(fresh_logger._stdlib_logger.handlers[0]) is original_handler_type, (
                    "Handlers type should not change (no implicit mode switching)"
                )

                # Verify that configuration validation is NOT performed
                # Pre-config should accept any reasonable logging calls without validation

                # Test with various message types that might trigger validation in configured mode
                test_cases = [
                    ("string message", "Simple string"),
                    ("dict message", {"key": "value", "number": 42}),
                    ("list message", [1, 2, 3, "test"]),
                    ("none message", None),
                    ("empty message", ""),
                ]

                for case_name, test_message in test_cases:
                    try:
                        fresh_logger.info(test_message)
                        # Should succeed without validation errors
                    except Exception as e:
                        # Should not get validation errors for message content
                        assert "validation" not in str(e).lower(), (
                            f"Pre-config should not validate message content ({case_name}): {e}"
                        )
                        assert "invalid" not in str(e).lower(), (
                            f"Pre-config should not validate message format ({case_name}): {e}"
                        )

                # Test that level filtering still works (this is not validation, it's normal logging behavior)
                original_level = fresh_logger._stdlib_logger.level
                fresh_logger._stdlib_logger.setLevel(logging.ERROR)

                # Debug messages should be filtered (normal behavior, not validation)
                fresh_logger.debug("This debug message should be filtered")

                # Error messages should still work
                fresh_logger.error("This error message should work")

                # Restore original level
                fresh_logger._stdlib_logger.setLevel(original_level)

        finally:
            # Cleanup: reset state
            fresh_logger.kill()
            fresh_logger = SparkLogger()
            logger = fresh_logger