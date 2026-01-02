"""
Test pre-configuration handler behavior including stderr usage and warning emission.
"""

import io
import logging
import os
import sys
from unittest.mock import patch

import pytest

from logspark.Handlers.PreConfig import pre_config_handler


class TestPreConfigHandlerStderrUsage:
    """Test pre-config handler stderr usage behavior"""

    def test_default_uses_stderr(self):
        """Test that pre-config handler uses stderr by default"""
        handler = pre_config_handler()

        # Should be StreamHandler with stderr
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream is sys.stderr

    def test_silenced_mode_uses_devnull(self):
        """Test that silenced mode redirects to devnull instead of stderr"""
        with patch.dict("os.environ", {"LOGSPARK_MODE": "silenced"}):
            handler = pre_config_handler()

            # Should not use stderr in silenced mode
            assert handler.stream is not sys.stderr
            # Should use devnull (exact implementation may vary)

    def test_normal_mode_stderr_explicit(self):
        """Test that normal mode explicitly uses stderr"""
        with patch.dict("os.environ", {}, clear=False):
            if "LOGSPARK_MODE" in os.environ:
                del os.environ["LOGSPARK_MODE"]

            handler = pre_config_handler()

            # Should use stderr in normal mode
            assert handler.stream is sys.stderr

    def test_handler_has_formatter(self):
        """Test that pre-config handler has proper formatter"""
        handler = pre_config_handler()

        # Should have a formatter
        assert handler.formatter is not None

        # Test formatter output format
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = handler.formatter.format(record)

        # Should contain expected elements
        assert "test.py:42" in formatted
        assert "WARNING" in formatted
        assert "Test message" in formatted


class TestPreConfigHandlerWarningEmission:
    """Test warning emission behavior"""

    def test_handler_emits_to_stderr(self):
        """Test that handler emits logs to stderr"""
        # Capture stderr
        with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            handler = pre_config_handler()

            # Create and emit a log record
            record = logging.LogRecord(
                name="test",
                level=logging.WARNING,
                pathname="test.py",
                lineno=1,
                msg="Test warning",
                args=(),
                exc_info=None,
            )

            handler.emit(record)

            # Verify output went to stderr
            stderr_output = mock_stderr.getvalue()
            assert "Test warning" in stderr_output
            assert "WARNING" in stderr_output

    def test_silenced_mode_no_stderr_output(self):
        """Test that silenced mode doesn't output to stderr"""
        with patch.dict("os.environ", {"LOGSPARK_MODE": "silenced"}):
            # Capture stderr
            with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
                handler = pre_config_handler()

                # Create and emit a log record
                record = logging.LogRecord(
                    name="test",
                    level=logging.WARNING,
                    pathname="test.py",
                    lineno=1,
                    msg="Test warning",
                    args=(),
                    exc_info=None,
                )

                handler.emit(record)

                # Verify no output went to stderr
                stderr_output = mock_stderr.getvalue()
                assert stderr_output == ""

    def test_multiple_handlers_independent(self):
        """Test that multiple pre-config handlers are independent"""
        handler1 = pre_config_handler()
        handler2 = pre_config_handler()

        # Should be different instances
        assert handler1 is not handler2

        # Both should use stderr (unless silenced)
        if os.environ.get("LOGSPARK_MODE") != "silenced":
            assert handler1.stream is sys.stderr
            assert handler2.stream is sys.stderr


class TestPreConfigHandlerInstallation:
    """Test handler installation behavior"""

    def test_handler_creation_returns_streamhandler(self):
        """Test that pre_config_handler returns a StreamHandler instance"""
        handler = pre_config_handler()

        assert isinstance(handler, logging.StreamHandler)
        assert hasattr(handler, "stream")
        assert hasattr(handler, "formatter")

    def test_handler_level_default(self):
        """Test that handler has appropriate default level"""
        handler = pre_config_handler()

        # Should have default level (NOTSET allows all levels through)
        assert handler.level == logging.NOTSET

    def test_handler_can_be_added_to_logger(self):
        """Test that handler can be properly added to a logger"""
        handler = pre_config_handler()
        logger = logging.getLogger("test_preconfig")

        # Should be able to add handler
        logger.addHandler(handler)

        # Verify handler is added
        assert handler in logger.handlers

        # Clean up
        logger.removeHandler(handler)

    def test_handler_formatting_consistency(self):
        """Test that handler formatting is consistent"""
        handler = pre_config_handler()

        # Create test records
        records = [
            logging.LogRecord(
                name="test1",
                level=logging.INFO,
                pathname="file1.py",
                lineno=10,
                msg="Message 1",
                args=(),
                exc_info=None,
            ),
            logging.LogRecord(
                name="test2",
                level=logging.ERROR,
                pathname="file2.py",
                lineno=20,
                msg="Message 2",
                args=(),
                exc_info=None,
            ),
        ]

        # Format records
        formatted_outputs = [handler.formatter.format(record) for record in records]

        # Verify consistent format structure
        for output in formatted_outputs:
            # Should contain time, file:line, level, and message
            assert " - " in output  # Separator
            assert ".py:" in output  # File and line
            assert " -> " in output  # Arrow separator


class TestPreConfigHandlerIntegration:
    """Integration tests for pre-config handler"""

    def test_handler_works_with_different_levels(self):
        """Test that handler works with different log levels"""
        handler = pre_config_handler()

        levels = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]

        for level in levels:
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="test.py",
                lineno=1,
                msg=f"Test {logging.getLevelName(level)}",
                args=(),
                exc_info=None,
            )

            # Should not raise exception
            try:
                handler.emit(record)
            except Exception as e:
                pytest.fail(f"Handler failed to emit {logging.getLevelName(level)} record: {e}")

    def test_handler_with_exception_info(self):
        """Test that handler handles exception information"""
        handler = pre_config_handler()

        # Create record with exception
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=None,
        )

        # Add exception info
        try:
            raise ValueError("Test exception")
        except ValueError:
            record.exc_info = sys.exc_info()

        # Should handle exception without error
        try:
            handler.emit(record)
        except Exception as e:
            pytest.fail(f"Handler failed to emit record with exception: {e}")

    def test_handler_environment_isolation(self):
        """Test that handler respects environment changes"""
        # Test normal mode
        with patch.dict("os.environ", {}, clear=False):
            if "LOGSPARK_MODE" in os.environ:
                del os.environ["LOGSPARK_MODE"]

            handler_normal = pre_config_handler()
            assert handler_normal.stream is sys.stderr

        # Test silenced mode
        with patch.dict("os.environ", {"LOGSPARK_MODE": "silenced"}):
            handler_silenced = pre_config_handler()
            assert handler_silenced.stream is not sys.stderr


# Property-Based Tests
from hypothesis import given
from hypothesis import strategies as st


class TestPreConfigHandlerProperties:
    """Property-based tests for pre-config handler behavior"""

    @given(
        message=st.text(min_size=1, max_size=500),
        level=st.sampled_from([
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ]),
        logger_name=st.text(
            min_size=1,
            max_size=100,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="._-"
            ),
        ),
        lineno=st.integers(min_value=1, max_value=10000),
    )
    def test_property_preconfig_stderr_usage(self, message, level, logger_name, lineno):
        """
        For any log message, pre-config handler should emit to stderr unless silenced
        """
        # Test normal mode (should use stderr)
        with patch.dict("os.environ", {}, clear=False):
            if "LOGSPARK_MODE" in os.environ:
                del os.environ["LOGSPARK_MODE"]

            handler = pre_config_handler()
            assert handler.stream is sys.stderr, "Handler should use stderr in normal mode"

        # Test silenced mode (should not use stderr)
        with patch.dict("os.environ", {"LOGSPARK_MODE": "silenced"}):
            handler_silenced = pre_config_handler()
            assert handler_silenced.stream is not sys.stderr, (
                "Handler should not use stderr in silenced mode"
            )

        # Test that handler can emit any message without error
        record = logging.LogRecord(
            name=logger_name,
            level=level,
            pathname="test.py",
            lineno=lineno,
            msg=message,
            args=(),
            exc_info=None,
        )

        # Should not raise exception for any valid input
        try:
            handler.emit(record)
        except Exception as e:
            pytest.fail(f"Handler failed to emit record: {e}")

    @given(
        messages=st.lists(st.text(min_size=1, max_size=200), min_size=1, max_size=10),
        level=st.sampled_from([logging.WARNING, logging.ERROR, logging.CRITICAL]),
    )
    def test_property_preconfig_warning_uniqueness(self, messages, level):
        """
        For any sequence of messages, each handler instance should emit warnings independently
        """
        # Create multiple handler instances
        handler1 = pre_config_handler()
        handler2 = pre_config_handler()

        # Handlers should be independent instances
        assert handler1 is not handler2, "Each call should create a new handler instance"

        # Both handlers should be able to emit all messages
        for i, message in enumerate(messages):
            record1 = logging.LogRecord(
                name="test1",
                level=level,
                pathname="test.py",
                lineno=i + 1,
                msg=message,
                args=(),
                exc_info=None,
            )
            record2 = logging.LogRecord(
                name="test2",
                level=level,
                pathname="test.py",
                lineno=i + 1,
                msg=message,
                args=(),
                exc_info=None,
            )

            # Both handlers should emit without interference
            try:
                handler1.emit(record1)
                handler2.emit(record2)
            except Exception as e:
                pytest.fail(f"Handler failed to emit message '{message}': {e}")

    @given(
        logger_names=st.lists(
            st.text(
                min_size=1,
                max_size=50,
                alphabet=st.characters(
                    whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="._-"
                ),
            ),
            min_size=1,
            max_size=5,
            unique=True,
        ),
        message=st.text(min_size=1, max_size=200),
    )
    def test_property_preconfig_handler_installation(self, logger_names, message):
        """
        For any set of logger names, pre-config handlers should install correctly on each logger
        """
        loggers = []
        handlers = []

        try:
            # Create handlers and install on loggers
            for logger_name in logger_names:
                logger = logging.getLogger(logger_name)
                handler = pre_config_handler()

                # Handler should install without error
                logger.addHandler(handler)

                # Verify installation
                assert handler in logger.handlers, (
                    f"Handler should be installed on logger '{logger_name}'"
                )

                loggers.append(logger)
                handlers.append(handler)

            # Test that each logger can emit messages independently
            for i, (logger, handler) in enumerate(zip(loggers, handlers, strict=False)):
                record = logging.LogRecord(
                    name=logger.name,
                    level=logging.INFO,
                    pathname="test.py",
                    lineno=i + 1,
                    msg=f"{message} - {i}",
                    args=(),
                    exc_info=None,
                )

                # Should emit without error
                try:
                    handler.emit(record)
                except Exception as e:
                    pytest.fail(f"Handler failed to emit on logger '{logger.name}': {e}")

        finally:
            # Clean up - remove handlers from loggers
            for logger, handler in zip(loggers, handlers, strict=False):
                if handler in logger.handlers:
                    logger.removeHandler(handler)

    @given(message=st.text(min_size=1, max_size=300), silenced=st.booleans())
    def test_property_preconfig_environment_consistency(self, message, silenced):
        """

        For any message and environment mode, handler behavior should be consistent with mode

        """
        env_patch = {"LOGSPARK_MODE": "silenced"} if silenced else {}

        with patch.dict("os.environ", env_patch, clear=False):
            if not silenced and "LOGSPARK_MODE" in os.environ:
                del os.environ["LOGSPARK_MODE"]

            handler = pre_config_handler()

            # Verify stream selection based on mode
            if silenced:
                assert handler.stream is not sys.stderr, "Silenced mode should not use stderr"
            else:
                assert handler.stream is sys.stderr, "Normal mode should use stderr"

            # Handler should work regardless of mode
            record = logging.LogRecord(
                name="test",
                level=logging.WARNING,
                pathname="test.py",
                lineno=1,
                msg=message,
                args=(),
                exc_info=None,
            )

            try:
                handler.emit(record)
            except Exception as e:
                pytest.fail(f"Handler failed in {'silenced' if silenced else 'normal'} mode: {e}")

    @given(messages=st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=20))
    def test_property_preconfig_formatter_consistency(self, messages):
        """

        For any sequence of messages, formatter should produce consistent output structure

        """
        handler = pre_config_handler()
        formatter = handler.formatter

        assert formatter is not None, "Handler should have a formatter"

        formatted_outputs = []

        for i, message in enumerate(messages):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=i + 1,
                msg=message,
                args=(),
                exc_info=None,
            )

            formatted = formatter.format(record)
            formatted_outputs.append(formatted)

            # Verify consistent format structure
            assert " - " in formatted, "Output should contain separator"
            assert "test.py:" in formatted, "Output should contain file and line"
            assert " -> " in formatted, "Output should contain arrow separator"
            assert message in formatted, "Output should contain the message"

        # All outputs should follow the same structural pattern
        for output in formatted_outputs:
            parts = output.split(" -> ")
            assert len(parts) == 2, "Output should have exactly one arrow separator"
