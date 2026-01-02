"""
Test adoption behavior for LogSpark manager.

Tests adopt_all() timing semantics, managed() identity guarantees,
and post-adoption logger handling.
"""

import logging

import pytest
from hypothesis import given
from hypothesis import strategies as st

from logspark import spark_log_manager


class TestAdoption:
    """Test logger adoption behavior and timing semantics."""

    def test_adopt_all_timing_snapshot(self, fresh_log_manager):
        """Test that adopt_all() only adopts loggers present at call time."""
        # Create some loggers before adoption
        logging.getLogger("test.before.1")
        logging.getLogger("test.before.2")

        # Adopt all current loggers
        fresh_log_manager.adopt_all(ignore_spark=False)

        # Verify pre-adoption loggers are managed
        managed_names = fresh_log_manager.managed_names
        assert "test.before.1" in managed_names
        assert "test.before.2" in managed_names

        # Create loggers after adoption
        logging.getLogger("test.after.1")
        logging.getLogger("test.after.2")

        # Verify post-adoption loggers are NOT managed
        managed_names_after = fresh_log_manager.managed_names
        assert "test.after.1" not in managed_names_after
        assert "test.after.2" not in managed_names_after

        # Verify original loggers are still managed
        assert "test.before.1" in managed_names_after
        assert "test.before.2" in managed_names_after

    def test_managed_returns_same_instance(self, fresh_log_manager):
        """Test that managed() returns the same stdlib Logger instance."""
        # Create and adopt a logger
        original_logger = logging.getLogger("test.identity")
        fresh_log_manager.adopt(original_logger)

        # Retrieve via managed()
        managed_logger = fresh_log_manager.managed("test.identity")

        # Verify it's the exact same instance
        assert managed_logger is original_logger
        assert id(managed_logger) == id(original_logger)

    def test_managed_keyerror_for_unmanaged(self, fresh_log_manager):
        """Test that managed() raises KeyError for unmanaged loggers."""
        # Create logger but don't adopt it
        logging.getLogger("test.unmanaged")

        # Verify KeyError is raised
        with pytest.raises(KeyError, match="Logger 'test.unmanaged' is not managed"):
            fresh_log_manager.managed("test.unmanaged")

    def test_adopt_all_ignores_placeholders(self, fresh_log_manager):
        """Test that adopt_all() ignores PlaceHolder entries in logging registry."""
        # Create a logger hierarchy that will create placeholders
        child_logger = logging.getLogger("parent.child.grandchild")

        # Adopt all loggers
        fresh_log_manager.adopt_all(ignore_spark=False)

        # Verify only concrete Logger instances are adopted
        managed_names = fresh_log_manager.managed_names
        assert "parent.child.grandchild" in managed_names

        # Verify we can retrieve the concrete logger
        retrieved = fresh_log_manager.managed("parent.child.grandchild")
        assert isinstance(retrieved, logging.Logger)
        assert retrieved is child_logger

    def test_adopt_all_ignore_list(self, fresh_log_manager):
        """Test that adopt_all() respects the ignore list."""
        # Create loggers
        logging.getLogger("test.include")
        logging.getLogger("test.exclude")

        # Adopt all except the excluded one
        fresh_log_manager.adopt_all(ignore=["test.exclude"], ignore_spark=False)

        managed_names = fresh_log_manager.managed_names
        assert "test.include" in managed_names
        assert "test.exclude" not in managed_names

    def test_adopt_all_ignore_spark_default(self, fresh_log_manager):
        """Test that adopt_all() ignores LogSpark logger by default."""
        # Create LogSpark logger
        logging.getLogger("LogSpark")

        # Adopt all with default ignore_spark=True
        fresh_log_manager.adopt_all()

        managed_names = fresh_log_manager.managed_names
        assert "LogSpark" not in managed_names

    def test_adopt_all_include_spark_when_requested(self, fresh_log_manager):
        """Test that adopt_all() can include LogSpark when ignore_spark=False."""
        # Create LogSpark logger
        logging.getLogger("LogSpark")

        # Adopt all including LogSpark
        fresh_log_manager.adopt_all(ignore_spark=False)

        managed_names = fresh_log_manager.managed_names
        assert "LogSpark" in managed_names

    def test_adopt_single_logger(self, fresh_log_manager):
        """Test adopting a single logger via adopt()."""
        logger = logging.getLogger("test.single")

        # Adopt single logger
        fresh_log_manager.adopt(logger)

        # Verify it's managed
        assert "test.single" in fresh_log_manager.managed_names
        assert fresh_log_manager.managed("test.single") is logger

    def test_post_adoption_loggers_unmanaged(self, fresh_log_manager):
        """Test that loggers created after adopt_all() remain unmanaged."""
        # Initial adoption
        fresh_log_manager.adopt_all()
        initial_count = len(fresh_log_manager.managed_names)

        # Create new loggers
        logging.getLogger("test.new.1")
        logging.getLogger("test.new.2")

        # Verify count hasn't changed
        assert len(fresh_log_manager.managed_names) == initial_count

        # Verify new loggers are not managed
        with pytest.raises(KeyError):
            fresh_log_manager.managed("test.new.1")
        with pytest.raises(KeyError):
            fresh_log_manager.managed("test.new.2")


class TestAdoptionProperties:
    """Property-based tests for adoption behavior."""

    @given(st.integers(min_value=1, max_value=5))
    def test_adoption_timing_property(self, num_loggers):
        """
        For any set of logger names, adopt_all() should only adopt loggers
        present at call time, not loggers created afterward.
        """
        # Get fresh manager instance for this test
        spark_log_manager.release_all()

        # Use unique test ID to avoid conflicts
        import uuid

        test_id = str(uuid.uuid4())[:8]

        # Create loggers before adoption
        pre_loggers = []
        for i in range(num_loggers):
            logger = logging.getLogger(f"pre.{test_id}.{i}")
            pre_loggers.append(logger)

        # Perform adoption - this should capture only pre-existing loggers
        spark_log_manager.adopt_all(ignore_spark=False)

        # Create loggers after adoption
        post_loggers = []
        for i in range(num_loggers):
            logger = logging.getLogger(f"post.{test_id}.{i}")
            post_loggers.append(logger)

        managed_names = spark_log_manager.managed_names

        # Verify pre-adoption loggers are managed
        for logger in pre_loggers:
            assert logger.name in managed_names, (
                f"Pre-adoption logger {logger.name} should be managed"
            )

        # Verify post-adoption loggers are NOT managed
        for logger in post_loggers:
            assert logger.name not in managed_names, (
                f"Post-adoption logger {logger.name} should NOT be managed"
            )

    @given(st.text(min_size=1, max_size=50))
    def test_managed_logger_identity_property(self, logger_name):
        """
        For any logger name, managed() should return the exact same stdlib Logger instance
        that was originally adopted.
        """
        # Get fresh manager instance for this test
        spark_log_manager.release_all()

        # Filter invalid characters for logger names
        if not all(c.isalnum() or c in "._-" for c in logger_name):
            return

        # Avoid conflicts with special loggers
        if logger_name in ["LogSpark", "root"]:
            return

        test_name = f"test.identity.{logger_name}"

        # Create and adopt logger
        original_logger = logging.getLogger(test_name)
        spark_log_manager.adopt(original_logger)

        # Retrieve via managed()
        retrieved_logger = spark_log_manager.managed(test_name)

        # Verify exact identity
        assert retrieved_logger is original_logger
        assert id(retrieved_logger) == id(original_logger)
        assert retrieved_logger.name == original_logger.name


class TestLogManagerPassiveManagement:
    """Test logmanager passive management behavior"""

    @given(
        external_logger_names=st.lists(
            st.text(min_size=1, max_size=20).filter(lambda x: x.isidentifier() and x != "LogSpark"),
            min_size=1,
            max_size=5,
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

        # Create fresh logmanager instance
        fresh_manager = spark_log_manager

        # Reset singleton state properly
        fresh_manager.release_all()
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
            fresh_manager.release_all()

            # Clear external loggers from registry
            for logger_name in list(logging.Logger.manager.loggerDict.keys()):
                if logger_name.startswith("external."):
                    del logging.Logger.manager.loggerDict[logger_name]


class TestStdlibAPICompliance:
    """Test stdlib API compliance for managed loggers"""

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
        fresh_manager.release_all()

        try:
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
                for _i, (level, message) in enumerate(zip(log_levels, log_messages, strict=False)):
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
            fresh_manager.release_all()

            # Clear test loggers from registry
            for logger_name in list(logging.Logger.manager.loggerDict.keys()):
                if logger_name.startswith("stdlib."):
                    del logging.Logger.manager.loggerDict[logger_name]
