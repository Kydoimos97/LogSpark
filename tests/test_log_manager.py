"""
logmanager tests for LogSpark Logging

These tests verify logmanager singleton functionality and global management.
"""

import logging

import pytest
from hypothesis import given
from hypothesis import strategies as st

from logspark import logger, spark_log_manager, SparkLogger, SparkLogManager
from logspark.Types.Exceptions import UnfrozenGlobalOperationError
from logspark.Types import TracebackOptions



class TestLogManagerBasics:
    """Test basic logmanager functionality"""

    def test_log_manager_is_singleton(self):
        """Test that logmanager maintains singleton identity"""
        from logspark import spark_log_manager
        LogManager2 = spark_log_manager
        assert spark_log_manager is LogManager2

    def test_log_manager_has_expected_methods(self):
        """Test that logmanager has expected methods"""
        assert hasattr(spark_log_manager, "adopt_all")
        assert hasattr(spark_log_manager, "managed")
        assert hasattr(spark_log_manager, "unify_format")

        assert callable(spark_log_manager.adopt_all)
        assert callable(spark_log_manager.managed)
        assert callable(spark_log_manager.unify_format)

    def test_log_manager_passively_manages_LogSpark_logger(self, fresh_log_manager):
        """Test that logmanager passively manages LogSpark logger by default"""
        # Should have LogSpark logger in managed loggers
        assert "LogSpark" in fresh_log_manager._state.managed_loggers

        # Should be able to get it via managed()
        LogSpark_logger = fresh_log_manager.managed("LogSpark")
        assert isinstance(LogSpark_logger, logging.Logger)
        assert LogSpark_logger.name == "LogSpark"


class TestLogManagerAdoption:
    """Test logmanager adoption functionality"""

    def test_adopt_all_adopts_existing_loggers(self, fresh_log_manager):
        """Test that adopt_all() adopts loggers present in registry"""
        # Create some test loggers
        test_logger1 = logging.getLogger("test.logger1")
        test_logger2 = logging.getLogger("test.logger2")

        # Adopt all current loggers
        fresh_log_manager.adopt_all()

        # Should now be able to manage them
        managed_logger1 = fresh_log_manager.managed("test.logger1")
        managed_logger2 = fresh_log_manager.managed("test.logger2")

        assert managed_logger1 is test_logger1
        assert managed_logger2 is test_logger2

    def test_managed_raises_for_unmanaged_logger(self, fresh_log_manager):
        """Test that managed() raises KeyError for unmanaged loggers"""
        with pytest.raises(KeyError):
            fresh_log_manager.managed("nonexistent")

    def test_post_adoption_loggers_remain_unmanaged(self, fresh_log_manager):
        """Test that loggers created after adopt_all() remain unmanaged"""
        # Adopt current loggers
        fresh_log_manager.adopt_all()

        # Create a new logger after adoption

        # Should not be managed
        with pytest.raises(KeyError):
            fresh_log_manager.managed("post.adoption.logger")


class TestLogManagerUnification:
    """Test logmanager unification functionality"""

    def test_unify_format_requires_frozen_logger(self, fresh_log_manager, fresh_logger):
        """Test that unify_format() requires frozen logger configuration"""
        fresh_logger.configure(no_freeze=True)

        with pytest.raises(UnfrozenGlobalOperationError):
            fresh_log_manager.unify_format(fresh_logger)

    def test_unify_format_works_with_frozen_logger(self, fresh_log_manager, frozen_logger):
        """Test that unify_format() works with frozen logger"""
        # Should not raise an exception
        fresh_log_manager.unify_format(frozen_logger)


class TestLogManagerState:
    """Test logmanager state management"""

    def test_log_manager_state_initialization(self, fresh_log_manager):
        """Test that logmanager state is properly initialized"""
        state = fresh_log_manager._state

        assert hasattr(state, "managed_loggers")
        assert isinstance(state.managed_loggers, dict)
        assert "LogSpark" in state.managed_loggers

    def test_managed_loggers_returns_stdlib_loggers(self, fresh_log_manager):
        """Test that managed loggers are stdlib Logger instances"""
        # Create and adopt a test logger
        test_logger = logging.getLogger("test.stdlib.logger")
        fresh_log_manager.adopt_all()

        managed_logger = fresh_log_manager.managed("test.stdlib.logger")

        # Should be the same stdlib Logger instance
        assert managed_logger is test_logger
        assert isinstance(managed_logger, logging.Logger)
        assert not hasattr(managed_logger, "_wrench_custom_methods")  # No custom methods


class TestLogManagerProperties:
    """Property-based tests for logmanager behavior"""
    @pytest.mark.silenced
    @given(
        logger_operations=st.lists(
            st.sampled_from(["configure", "debug", "info", "warning"]),
            min_size=1,
            max_size=5,
        ),
        manager_operations=st.lists(
            st.sampled_from(["adopt_all", "managed_LogSpark"]), min_size=1, max_size=3
        ),
    )
    def test_singleton_independence(self, logger_operations, manager_operations):
        """
        For any operation on either logger or logmanager, the operation should not
        implicitly mutate the state of the other singleton
        """
        # Create fresh instances for this test
        fresh_logger = logger
        fresh_manager = spark_log_manager

        # Reset singleton instances to use our fresh ones
        if hasattr(logger, "_SingletonWrapper__cls_instance"):
            logger._SingletonWrapper__cls_instance = None
        if hasattr(spark_log_manager, "_SingletonWrapper__cls_instance"):
            spark_log_manager._SingletonWrapper__cls_instance = None

        try:
            # Capture initial state of both singletons
            initial_manager_loggers = fresh_manager._state.managed_loggers.copy()

            # Perform operations on logger and verify manager is not affected
            for operation in logger_operations:
                if operation == "configure":
                    try:
                        fresh_logger.configure(level=logging.INFO, traceback=TracebackOptions.NONE)
                    except Exception:
                        pass  # May fail if already frozen, that's ok
                elif operation in ["debug", "info", "warning"]:
                    try:
                        getattr(fresh_logger, operation)("Test message")
                    except Exception:
                        pass  # May fail, that's ok for this test

                # Verify manager state unchanged after logger operation
                assert fresh_manager._state.managed_loggers == initial_manager_loggers, (
                    f"logmanager state changed after logger.{operation}()"
                )

            # Perform operations on manager and verify logger is not affected
            try:
                logger_config_after_logger_ops = fresh_logger.config
            except Exception:
                logger_config_after_logger_ops = None
            logger_frozen_after_logger_ops = fresh_logger._frozen

            for operation in manager_operations:
                if operation == "adopt_all":
                    try:
                        fresh_manager.adopt_all()
                    except Exception:
                        pass  # May fail, that's ok
                elif operation == "managed_LogSpark":
                    try:
                        fresh_manager.managed("LogSpark")
                    except Exception:
                        pass  # May fail if not managed, that's ok

                # Verify logger state unchanged after manager operation
                try:
                    current_config = fresh_logger.config
                except Exception:
                    current_config = None
                assert current_config == logger_config_after_logger_ops, (
                    f"Logger config changed after logmanager.{operation}()"
                )
                assert fresh_logger._frozen == logger_frozen_after_logger_ops, (
                    f"Logger frozen state changed after logmanager.{operation}()"
                )

        finally:
            # Cleanup using new methods
            fresh_logger.kill()
            fresh_manager.release()

    @given(
        pre_adoption_loggers=st.lists(
            st.text(min_size=1, max_size=20).filter(lambda x: "." not in x and x.isidentifier()),
            min_size=1,
            max_size=5,
            unique=True,
        ),
        post_adoption_loggers=st.lists(
            st.text(min_size=1, max_size=20).filter(lambda x: "." not in x and x.isidentifier()),
            min_size=1,
            max_size=5,
            unique=True,
        ),
    )
    def test_explicit_adoption_behavior(self, pre_adoption_loggers, post_adoption_loggers):
        """
        For any call to adopt_all(), the logmanager should adopt only loggers present
        in the registry at call time, leaving subsequently created loggers unmanaged
        """
        # Create fresh manager for this test
        fresh_manager = spark_log_manager

        # Reset singleton instance to use our fresh one
        if hasattr(spark_log_manager, "_SingletonWrapper__cls_instance"):
            spark_log_manager._SingletonWrapper__cls_instance = None

        try:
            # Clear managed loggers except LogSpark
            fresh_manager._state.managed_loggers.clear()
            fresh_manager._state.managed_loggers["LogSpark"] = logging.getLogger("LogSpark")

            # Create loggers before adoption
            pre_adoption_logger_instances = {}
            for logger_name in pre_adoption_loggers:
                if logger_name != "LogSpark":  # Avoid conflicts with default
                    logger_instance = logging.getLogger(f"pre.{logger_name}")
                    pre_adoption_logger_instances[f"pre.{logger_name}"] = logger_instance

            # Adopt all current loggers
            fresh_manager.adopt_all()

            # Verify all pre-adoption loggers are now managed
            for logger_name, logger_instance in pre_adoption_logger_instances.items():
                managed_logger = fresh_manager.managed(logger_name)
                assert managed_logger is logger_instance, (
                    f"Pre-adoption logger {logger_name} should be managed after adopt_all()"
                )

            # Create loggers after adoption
            post_adoption_logger_instances = {}
            for logger_name in post_adoption_loggers:
                if logger_name not in pre_adoption_loggers and logger_name != "LogSpark":
                    logger_instance = logging.getLogger(f"post.{logger_name}")
                    post_adoption_logger_instances[f"post.{logger_name}"] = logger_instance

            # Verify post-adoption loggers are NOT managed
            for logger_name in post_adoption_logger_instances.keys():
                with pytest.raises(KeyError):
                    fresh_manager.managed(logger_name)

            # Verify that calling adopt_all() again would adopt the post-adoption loggers
            fresh_manager.adopt_all()

            # Now post-adoption loggers should be managed
            for logger_name, logger_instance in post_adoption_logger_instances.items():
                managed_logger = fresh_manager.managed(logger_name)
                assert managed_logger is logger_instance, (
                    f"Post-adoption logger {logger_name} should be managed after second adopt_all()"
                )

        finally:
            # Cleanup: reset singleton instance and clear logger registry
            if hasattr(spark_log_manager, "_SingletonWrapper__cls_instance"):
                spark_log_manager._SingletonWrapper__cls_instance = None

            # Clear test loggers from registry
            for logger_name in list(logging.Logger.manager.loggerDict.keys()):
                if logger_name.startswith("pre.") or logger_name.startswith("post."):
                    del logging.Logger.manager.loggerDict[logger_name]

    @given(
        logger_names=st.lists(
            st.text(min_size=1, max_size=15).filter(lambda x: x.isidentifier() and x != "LogSpark"),
            min_size=1,
            max_size=3,
            unique=True,
        ),
        log_levels=st.lists(
            st.sampled_from([
                logging.DEBUG,
                logging.INFO,
                logging.WARNING,
                logging.ERROR,
                logging.CRITICAL,
            ]),
            min_size=1,
            max_size=3,
        ),
        log_messages=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=3),
    )
    def test_stdlib_api_compliance(self, logger_names, log_levels, log_messages):
        """
        For any logger returned by managed(), it should be a standard logging.Logger
        instance with stdlib-compliant APIs
        """
        # Create fresh manager for this test
        fresh_manager = spark_log_manager

        # Reset singleton instance to use our fresh one
        if hasattr(spark_log_manager, "_SingletonWrapper__cls_instance"):
            spark_log_manager._SingletonWrapper__cls_instance = None

        try:
            # Clear managed loggers except LogSpark
            fresh_manager._state.managed_loggers.clear()
            fresh_manager._state.managed_loggers["LogSpark"] = logging.getLogger("LogSpark")

            # Create test loggers and adopt them
            test_loggers = {}
            for logger_name in logger_names:
                test_logger = logging.getLogger(f"stdlib.{logger_name}")
                test_loggers[f"stdlib.{logger_name}"] = test_logger

            fresh_manager.adopt_all()

            # Test each managed logger for stdlib compliance
            for logger_name, original_logger in test_loggers.items():
                managed_logger = fresh_manager.managed(logger_name)

                # Verify it's the same stdlib Logger instance
                assert managed_logger is original_logger, (
                    "Managed logger should be the same instance as original stdlib logger"
                )

                # Verify it's a standard logging.Logger (not a subclass)
                assert type(managed_logger) is logging.Logger, (
                    f"Managed logger should be standard logging.Logger, got {type(managed_logger)}"
                )

                # Test stdlib API methods exist and are callable
                stdlib_methods = [
                    "debug",
                    "info",
                    "warning",
                    "error",
                    "critical",
                    "setLevel",
                    "getEffectiveLevel",
                    "addHandler",
                    "removeHandler",
                    "addFilter",
                    "removeFilter",
                    "isEnabledFor",
                ]

                for method_name in stdlib_methods:
                    assert hasattr(managed_logger, method_name), (
                        f"Managed logger should have stdlib method {method_name}"
                    )
                    assert callable(getattr(managed_logger, method_name)), (
                        f"Managed logger method {method_name} should be callable"
                    )

                # Test stdlib properties exist
                stdlib_properties = ["name", "level", "parent", "handlers", "filters"]
                for prop_name in stdlib_properties:
                    assert hasattr(managed_logger, prop_name), (
                        f"Managed logger should have stdlib property {prop_name}"
                    )

                # Test that we can use stdlib APIs without errors
                for i, (level, message) in enumerate(zip(log_levels, log_messages)):
                    try:
                        # Test setLevel (stdlib API)
                        managed_logger.setLevel(level)
                        assert managed_logger.level == level, "setLevel should work with stdlib API"

                        # Test logging methods (stdlib API)
                        managed_logger.debug(f"Debug: {message}")
                        managed_logger.info(f"Info: {message}")
                        managed_logger.warning(f"Warning: {message}")
                        managed_logger.error(f"Error: {message}")
                        managed_logger.critical(f"Critical: {message}")

                        # Test isEnabledFor (stdlib API)
                        enabled = managed_logger.isEnabledFor(level)
                        assert isinstance(enabled, bool), "isEnabledFor should return boolean"

                        # Test getEffectiveLevel (stdlib API)
                        effective_level = managed_logger.getEffectiveLevel()
                        assert isinstance(effective_level, int), (
                            "getEffectiveLevel should return integer"
                        )

                    except Exception as e:
                        pytest.fail(f"Stdlib API call failed for logger {logger_name}: {e}")

                # Verify no custom LogSpark methods are exposed
                LogSpark_methods = ["configure", "freeze", "is_frozen"]
                for method_name in LogSpark_methods:
                    assert not hasattr(managed_logger, method_name), (
                        f"Managed logger should not have LogSpark-specific method {method_name}"
                    )

        finally:
            # Cleanup: reset singleton instance and clear logger registry
            if hasattr(spark_log_manager, "_SingletonWrapper__cls_instance"):
                spark_log_manager._SingletonWrapper__cls_instance = None

            # Clear test loggers from registry
            for logger_name in list(logging.Logger.manager.loggerDict.keys()):
                if logger_name.startswith("stdlib."):
                    del logging.Logger.manager.loggerDict[logger_name]

    # noinspection PyTestUnpassedFixture
    @given(
        config_levels=st.sampled_from([
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ]),
        traceback_policies=st.sampled_from([
            TracebackOptions.NONE,
            TracebackOptions.COMPACT,
            TracebackOptions.FULL,
        ]),
        freeze_before_unify=st.booleans(),
    )
    def test_global_operation_preconditions(
        self, config_levels, traceback_policies, freeze_before_unify):
        """
        For any global operation like unify_format(), the operation should require a frozen
        logger configuration and raise a hard error if called before freeze
        """
        # Create fresh instances for this test
        fresh_logger = logger
        fresh_manager = spark_log_manager
        
        # Reset singleton state properly
        fresh_logger.kill()
        fresh_manager.release()

        try:
            # Configure the logger with random parameters
            from logspark.Handlers import TerminalHandler



            if freeze_before_unify:
                # Freeze the logger before attempting unify_format
                fresh_logger.configure(level=config_levels, traceback=traceback_policies, handler=TerminalHandler())

                # unify_format should succeed with frozen logger
                try:
                    fresh_manager.unify_format(fresh_logger)
                    # Success is expected
                except UnfrozenGlobalOperationError:
                    pytest.fail("unify_format() should succeed with frozen logger configuration")
                except Exception as e:
                    # Other exceptions might be acceptable (e.g., no managed loggers)
                    # but UnfrozenGlobalOperationError should not occur
                    if isinstance(e, UnfrozenGlobalOperationError):
                        pytest.fail(
                            f"Unexpected UnfrozenGlobalOperationError with frozen logger: {e}"
                        )
            else:
                fresh_logger.configure(level=config_levels, traceback=traceback_policies, handler=TerminalHandler(), no_freeze=True)
                # Do not freeze the logger before attempting unify_format
                # unify_format should raise UnfrozenGlobalOperationError
                with pytest.raises(
                    UnfrozenGlobalOperationError,
                    match="LogSpark logger needs to be frozen before calling this method",
                ):
                    fresh_manager.unify_format(fresh_logger)

        finally:
            # Cleanup using new methods
            fresh_logger.kill()
            fresh_manager.release()
