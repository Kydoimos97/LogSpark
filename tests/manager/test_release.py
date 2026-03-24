"""
Test release behavior for LogSpark manager.

Tests release_all() cleanup, reference management,
and individual logger release behavior.
"""

import logging

import pytest
from hypothesis import given
from hypothesis import strategies as st

from logspark import spark_log_manager


class TestRelease:
    """Test release behavior for logger cleanup and reference management."""

    def test_release_all_clears_references(self, fresh_log_manager):
        """Test that release_all() clears all managed logger references."""
        # Create and adopt multiple loggers
        logger1 = logging.getLogger("test.release.1")
        logger2 = logging.getLogger("test.release.2")
        logger3 = logging.getLogger("test.release.3")

        fresh_log_manager.adopt(logger1)
        fresh_log_manager.adopt(logger2)
        fresh_log_manager.adopt(logger3)

        # Verify loggers are managed
        managed_names = fresh_log_manager.managed_names
        assert "test.release.1" in managed_names
        assert "test.release.2" in managed_names
        assert "test.release.3" in managed_names
        assert len(managed_names) >= 3

        # Release all
        fresh_log_manager.release_all()

        # Verify all references are cleared
        managed_names_after = fresh_log_manager.managed_names
        assert "test.release.1" not in managed_names_after
        assert "test.release.2" not in managed_names_after
        assert "test.release.3" not in managed_names_after

    def test_release_all_resets_manager_state(self, fresh_log_manager):
        """Test that release_all() resets manager to clean baseline."""
        # Adopt some loggers
        logger1 = logging.getLogger("test.state.1")
        logger2 = logging.getLogger("test.state.2")
        fresh_log_manager.adopt(logger1)
        fresh_log_manager.adopt(logger2)

        # Verify loggers are managed
        assert len(fresh_log_manager.managed_names) >= 2

        # Release all
        fresh_log_manager.release_all()

        # Verify manager is in clean state
        # Should only have LogSpark logger by default
        managed_names = fresh_log_manager.managed_names
        assert "LogSpark" in managed_names
        assert len(managed_names) == 1

    def test_release_single_logger(self, fresh_log_manager):
        """Test releasing a single logger via release()."""
        # Create and adopt loggers
        logger1 = logging.getLogger("test.single.1")
        logger2 = logging.getLogger("test.single.2")
        fresh_log_manager.adopt(logger1)
        fresh_log_manager.adopt(logger2)

        # Verify both are managed
        managed_names = fresh_log_manager.managed_names
        assert "test.single.1" in managed_names
        assert "test.single.2" in managed_names

        # Release one logger
        fresh_log_manager.release("test.single.1")

        # Verify only the released logger is gone
        managed_names_after = fresh_log_manager.managed_names
        assert "test.single.1" not in managed_names_after
        assert "test.single.2" in managed_names_after

    def test_release_nonexistent_logger_error(self, fresh_log_manager):
        """Test that release() raises KeyError for non-managed logger."""
        # Try to release a logger that was never adopted
        with pytest.raises(KeyError, match="Logger 'nonexistent' is not managed"):
            fresh_log_manager.release("nonexistent")

    def test_release_all_preserves_logger_functionality(self, fresh_log_manager):
        """Test that release_all() doesn't affect logger functionality."""
        # Create and adopt logger
        logger = logging.getLogger("test.functionality")
        fresh_log_manager.adopt(logger)

        # Add handler and configure logger
        import io

        test_stream = io.StringIO()
        handler = logging.StreamHandler(test_stream)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Release all
        fresh_log_manager.release_all()

        # Verify logger still works
        logger.info("test message")
        output = test_stream.getvalue()
        assert "test message" in output

        # Verify logger configuration is preserved
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1

    def test_release_all_multiple_calls(self, fresh_log_manager):
        """Test that multiple release_all() calls are safe."""
        # Adopt some loggers
        logger = logging.getLogger("test.multiple")
        fresh_log_manager.adopt(logger)

        # First release_all()
        fresh_log_manager.release_all()
        managed_after_first = fresh_log_manager.managed_names

        # Second release_all()
        fresh_log_manager.release_all()
        managed_after_second = fresh_log_manager.managed_names

        # Should be in same state
        assert managed_after_first == managed_after_second
        assert "LogSpark" in managed_after_second
        assert len(managed_after_second) == 1

    def test_release_all_thread_safety(self, fresh_log_manager):
        """Test that release_all() is thread-safe."""
        import threading
        import time

        # Create loggers
        loggers = [logging.getLogger(f"test.thread.{i}") for i in range(10)]
        for logger in loggers:
            fresh_log_manager.adopt(logger)

        # Function to release all in thread
        def release_in_thread():
            time.sleep(0.01)  # Small delay to increase chance of race condition
            fresh_log_manager.release_all()

        # Start multiple threads
        threads = [threading.Thread(target=release_in_thread) for _ in range(3)]
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify final state is consistent
        managed_names = fresh_log_manager.managed_names
        assert "LogSpark" in managed_names
        assert len(managed_names) == 1

    def test_release_preserves_other_loggers(self, fresh_log_manager):
        """Test that releasing one logger doesn't affect others."""
        # Create and adopt multiple loggers
        logger1 = logging.getLogger("test.preserve.1")
        logger2 = logging.getLogger("test.preserve.2")
        logger3 = logging.getLogger("test.preserve.3")

        fresh_log_manager.adopt(logger1)
        fresh_log_manager.adopt(logger2)
        fresh_log_manager.adopt(logger3)

        # Release middle logger
        fresh_log_manager.release("test.preserve.2")

        # Verify others are still managed and accessible
        assert fresh_log_manager.managed("test.preserve.1") is logger1
        assert fresh_log_manager.managed("test.preserve.3") is logger3

        # Verify released logger is not managed
        with pytest.raises(KeyError):
            fresh_log_manager.managed("test.preserve.2")

    def test_release_all_after_unify(self, fresh_log_manager, test_handler):
        """Test that release_all() works correctly after unify operations."""
        # Create and adopt loggers
        logger1 = logging.getLogger("test.unify.release.1")
        logger2 = logging.getLogger("test.unify.release.2")

        fresh_log_manager.adopt(logger1)
        fresh_log_manager.adopt(logger2)

        # Apply unify configuration
        fresh_log_manager.unify(handlers=[test_handler], level=logging.WARNING)

        # Verify configuration was applied
        assert logger1.handlers[0] is test_handler
        assert logger2.handlers[0] is test_handler
        assert logger1.level == logging.WARNING
        assert logger2.level == logging.WARNING

        # Release all
        fresh_log_manager.release_all()

        # Verify loggers are no longer managed
        managed_names = fresh_log_manager.managed_names
        assert "test.unify.release.1" not in managed_names
        assert "test.unify.release.2" not in managed_names

        # Verify logger configuration is preserved (release doesn't undo unify)
        assert logger1.handlers[0] is test_handler
        assert logger2.handlers[0] is test_handler
        assert logger1.level == logging.WARNING
        assert logger2.level == logging.WARNING


class TestReleaseProperties:
    """Property-based tests for release behavior."""

    @given(st.integers(min_value=1, max_value=20))
    def test_release_cleanup_property(self, num_loggers):
        """
        For any release_all() call, all managed logger references should be cleared.
        """
        # Get fresh manager instance
        spark_log_manager.release_all()

        # Create and adopt multiple loggers
        loggers = []
        for i in range(num_loggers):
            logger = logging.getLogger(f"test.cleanup.prop.{i}")
            loggers.append(logger)
            spark_log_manager.adopt(logger)

        # Verify loggers are managed
        managed_names_before = spark_log_manager.managed_names
        for logger in loggers:
            assert logger.name in managed_names_before

        # Release all
        spark_log_manager.release_all()

        # Verify all references are cleared
        managed_names_after = spark_log_manager.managed_names
        for logger in loggers:
            assert logger.name not in managed_names_after

        # Verify manager is in clean baseline state
        assert "LogSpark" in managed_names_after
        assert len(managed_names_after) == 1
