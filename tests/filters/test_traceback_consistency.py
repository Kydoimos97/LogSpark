"""
Test identical traceback semantics across all handlers.

This module tests that traceback policies produce consistent behavior
across different handler types (Terminal, JSON, PreConfig).
"""

import io
import logging
import sys

import pytest

from logspark._Internal.Func.configure_handler_traceback_policy import (
    configure_handler_traceback_policy,
)
from logspark.Types.Options import TracebackOptions


class TestTracebackConsistencyAcrossHandlers:
    """Test identical traceback semantics across all handlers"""

    def test_compact_policy_consistency_terminal_vs_json(self):
        """Test that COMPACT policy is applied consistently between Terminal and JSON handlers"""
        # Skip if JSON handler dependencies are not available
        pytest.importorskip("pythonjsonlogger")

        from logspark.Handlers.Json import SparkJSONHandler
        from logspark.Handlers.Terminal import SparkTerminalHandler

        # Create handlers
        terminal_stream = io.StringIO()
        terminal_handler = SparkTerminalHandler(stream=terminal_stream)
        configure_handler_traceback_policy(terminal_handler, TracebackOptions.COMPACT)

        json_stream = io.StringIO()
        json_handler = SparkJSONHandler(stream=json_stream)
        configure_handler_traceback_policy(json_handler, TracebackOptions.COMPACT)

        # Create identical records with exception
        try:
            raise ValueError("Test exception for consistency")
        except ValueError:
            exc_info = sys.exc_info()

        terminal_record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        json_record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        # Process records through filters to set traceback policy
        for filter_obj in terminal_handler.filters:
            filter_obj.filter(terminal_record)

        for filter_obj in json_handler.filters:
            filter_obj.filter(json_record)

        # Both records should have the same traceback policy
        assert hasattr(terminal_record, "traceback_policy")
        assert hasattr(json_record, "traceback_policy")
        assert terminal_record.traceback_policy == TracebackOptions.COMPACT
        assert json_record.traceback_policy == TracebackOptions.COMPACT

        # Emit records (handlers will process the traceback policy)
        terminal_handler.emit(terminal_record)
        json_handler.emit(json_record)

        # Both handlers should have processed the records without error
        terminal_output = terminal_stream.getvalue()
        json_output = json_stream.getvalue()

        assert len(terminal_output) > 0
        assert len(json_output) > 0

    def test_full_policy_consistency_terminal_vs_json(self):
        """Test that FULL policy is applied consistently between Terminal and JSON handlers"""
        # Skip if JSON handler dependencies are not available
        pytest.importorskip("pythonjsonlogger")

        from logspark.Handlers.Json import SparkJSONHandler
        from logspark.Handlers.Terminal import SparkTerminalHandler

        # Create handlers
        terminal_stream = io.StringIO()
        terminal_handler = SparkTerminalHandler(stream=terminal_stream)
        configure_handler_traceback_policy(terminal_handler, TracebackOptions.FULL)

        json_stream = io.StringIO()
        json_handler = SparkJSONHandler(stream=json_stream)
        configure_handler_traceback_policy(json_handler, TracebackOptions.FULL)

        # Create identical records with exception
        try:
            raise ValueError("Test exception for full consistency")
        except ValueError:
            exc_info = sys.exc_info()

        terminal_record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        json_record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        # Process records through filters to set traceback policy
        for filter_obj in terminal_handler.filters:
            filter_obj.filter(terminal_record)

        for filter_obj in json_handler.filters:
            filter_obj.filter(json_record)

        # Both records should have the same traceback policy
        assert hasattr(terminal_record, "traceback_policy")
        assert hasattr(json_record, "traceback_policy")
        assert terminal_record.traceback_policy == TracebackOptions.FULL
        assert json_record.traceback_policy == TracebackOptions.FULL

        # Emit records (handlers will process the traceback policy)
        terminal_handler.emit(terminal_record)
        json_handler.emit(json_record)

        # Both handlers should have processed the records without error
        terminal_output = terminal_stream.getvalue()
        json_output = json_stream.getvalue()

        assert len(terminal_output) > 0
        assert len(json_output) > 0

    def test_none_policy_consistency_across_all_handlers(self):
        """Test that NONE policy is applied consistently across all handler types"""
        from logspark.Handlers.PreConfig import pre_config_handler
        from logspark.Handlers.Terminal import SparkTerminalHandler

        # Create handlers
        terminal_stream = io.StringIO()
        terminal_handler = SparkTerminalHandler(stream=terminal_stream)
        configure_handler_traceback_policy(terminal_handler, TracebackOptions.NONE)

        preconfig_handler = pre_config_handler()
        configure_handler_traceback_policy(preconfig_handler, TracebackOptions.NONE)

        # Create identical records with exception
        try:
            raise ValueError("Test exception for none consistency")
        except ValueError:
            exc_info = sys.exc_info()

        terminal_record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        preconfig_record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        # Process records through filters to set traceback policy
        for filter_obj in terminal_handler.filters:
            filter_obj.filter(terminal_record)

        for filter_obj in preconfig_handler.filters:
            filter_obj.filter(preconfig_record)

        # Both records should have the same traceback policy
        assert hasattr(terminal_record, "traceback_policy")
        assert hasattr(preconfig_record, "traceback_policy")
        assert terminal_record.traceback_policy == TracebackOptions.NONE
        assert preconfig_record.traceback_policy == TracebackOptions.NONE

        # Emit records (handlers will process the traceback policy)
        terminal_handler.emit(terminal_record)
        preconfig_handler.emit(preconfig_record)

        # Both handlers should have processed the records without error
        terminal_output = terminal_stream.getvalue()
        # Note: preconfig_handler output goes to stderr or devnull, so we can't easily capture it
        assert len(terminal_output) > 0

    def test_cross_handler_policy_isolation(self):
        """Test that different handlers can have different traceback policies without interference"""
        from logspark.Handlers.PreConfig import pre_config_handler
        from logspark.Handlers.Terminal import SparkTerminalHandler

        # Create handlers with different policies
        terminal_stream = io.StringIO()
        terminal_handler = SparkTerminalHandler(stream=terminal_stream)
        configure_handler_traceback_policy(terminal_handler, TracebackOptions.COMPACT)

        preconfig_handler = pre_config_handler()
        configure_handler_traceback_policy(preconfig_handler, TracebackOptions.FULL)

        # Create identical records
        try:
            raise ValueError("Test exception for policy isolation")
        except ValueError:
            exc_info = sys.exc_info()

        terminal_record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        preconfig_record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        # Process records through filters
        for filter_obj in terminal_handler.filters:
            filter_obj.filter(terminal_record)

        for filter_obj in preconfig_handler.filters:
            filter_obj.filter(preconfig_record)

        # Records should have different traceback policies
        assert terminal_record.traceback_policy == TracebackOptions.COMPACT
        assert preconfig_record.traceback_policy == TracebackOptions.FULL

        # Emit records
        terminal_handler.emit(terminal_record)
        preconfig_handler.emit(preconfig_record)

        # Both handlers should have processed the records without error
        terminal_output = terminal_stream.getvalue()
        # Note: preconfig_handler output goes to stderr or devnull, so we can't easily capture it
        assert len(terminal_output) > 0

    def test_filter_order_independence(self):
        """Test that traceback policy filters work regardless of filter order"""
        from logspark.Handlers.Terminal import SparkTerminalHandler

        # Create handler and add custom filter before traceback policy
        terminal_stream = io.StringIO()
        terminal_handler = SparkTerminalHandler(stream=terminal_stream)

        # Add a custom filter first
        class CustomFilter(logging.Filter):
            def filter(self, record):
                record.custom_field = "test_value"
                return True

        terminal_handler.addFilter(CustomFilter())
        configure_handler_traceback_policy(terminal_handler, TracebackOptions.COMPACT)

        # Create record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Process through all filters
        for filter_obj in terminal_handler.filters:
            filter_obj.filter(record)

        # Both custom field and traceback policy should be set
        assert hasattr(record, "custom_field")
        assert record.custom_field == "test_value"
        assert hasattr(record, "traceback_policy")
        assert record.traceback_policy == TracebackOptions.COMPACT

        # Emit record
        terminal_handler.emit(record)

        # Handler should have processed the record without error
        output = terminal_stream.getvalue()
        assert len(output) > 0


# Property-based tests
from hypothesis import given
from hypothesis import strategies as st


class TestTracebackConsistencyProperties:
    """Property-based tests for traceback consistency across handlers"""

    @given(
        logger_name=st.text(
            min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)
        ),
        message=st.text(
            min_size=1, max_size=500, alphabet=st.characters(min_codepoint=32, max_codepoint=126)
        ),
        level=st.sampled_from([
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ]),
        lineno=st.integers(min_value=1, max_value=10000),
        exception_message=st.text(
            min_size=1, max_size=200, alphabet=st.characters(min_codepoint=32, max_codepoint=126)
        ),
    )
    def test_property_traceback_policy_compact_consistency(
        self, logger_name, message, level, lineno, exception_message
    ):
        """

        For any log record, COMPACT policy should be applied consistently across all handlers

        """
        from logspark.Handlers.PreConfig import pre_config_handler
        from logspark.Handlers.Terminal import SparkTerminalHandler

        # Create handlers with COMPACT policy
        terminal_stream = io.StringIO()
        terminal_handler = SparkTerminalHandler(stream=terminal_stream)
        configure_handler_traceback_policy(terminal_handler, TracebackOptions.COMPACT)

        preconfig_handler = pre_config_handler()
        configure_handler_traceback_policy(preconfig_handler, TracebackOptions.COMPACT)

        # Create identical records with exception
        try:
            raise ValueError(exception_message)
        except ValueError:
            exc_info = sys.exc_info()

        terminal_record = logging.LogRecord(
            name=logger_name,
            level=level,
            pathname="test.py",
            lineno=lineno,
            msg=message,
            args=(),
            exc_info=exc_info,
        )

        preconfig_record = logging.LogRecord(
            name=logger_name,
            level=level,
            pathname="test.py",
            lineno=lineno,
            msg=message,
            args=(),
            exc_info=exc_info,
        )

        # Process records through filters
        for filter_obj in terminal_handler.filters:
            filter_obj.filter(terminal_record)

        for filter_obj in preconfig_handler.filters:
            filter_obj.filter(preconfig_record)

        # Both records should have consistent COMPACT policy
        assert hasattr(terminal_record, "traceback_policy")
        assert hasattr(preconfig_record, "traceback_policy")
        assert terminal_record.traceback_policy == TracebackOptions.COMPACT
        assert preconfig_record.traceback_policy == TracebackOptions.COMPACT

        # Records should have identical core data
        assert terminal_record.name == preconfig_record.name
        assert terminal_record.msg == preconfig_record.msg
        assert terminal_record.levelno == preconfig_record.levelno
        assert terminal_record.lineno == preconfig_record.lineno

        # Emit records - should not raise exceptions
        terminal_handler.emit(terminal_record)
        preconfig_handler.emit(preconfig_record)

    @given(
        logger_name=st.text(
            min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)
        ),
        message=st.text(
            min_size=1, max_size=500, alphabet=st.characters(min_codepoint=32, max_codepoint=126)
        ),
        level=st.sampled_from([
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ]),
        lineno=st.integers(min_value=1, max_value=10000),
        exception_message=st.text(
            min_size=1, max_size=200, alphabet=st.characters(min_codepoint=32, max_codepoint=126)
        ),
    )
    def test_property_traceback_policy_full_consistency(
        self, logger_name, message, level, lineno, exception_message
    ):
        """

        For any log record, FULL policy should be handled consistently across all handlers

        """
        from logspark.Handlers.PreConfig import pre_config_handler
        from logspark.Handlers.Terminal import SparkTerminalHandler

        # Create handlers with FULL policy
        terminal_stream = io.StringIO()
        terminal_handler = SparkTerminalHandler(stream=terminal_stream)
        configure_handler_traceback_policy(terminal_handler, TracebackOptions.FULL)

        preconfig_handler = pre_config_handler()
        configure_handler_traceback_policy(preconfig_handler, TracebackOptions.FULL)

        # Create identical records with exception
        try:
            raise ValueError(exception_message)
        except ValueError:
            exc_info = sys.exc_info()

        terminal_record = logging.LogRecord(
            name=logger_name,
            level=level,
            pathname="test.py",
            lineno=lineno,
            msg=message,
            args=(),
            exc_info=exc_info,
        )

        preconfig_record = logging.LogRecord(
            name=logger_name,
            level=level,
            pathname="test.py",
            lineno=lineno,
            msg=message,
            args=(),
            exc_info=exc_info,
        )

        # Process records through filters
        for filter_obj in terminal_handler.filters:
            filter_obj.filter(terminal_record)

        for filter_obj in preconfig_handler.filters:
            filter_obj.filter(preconfig_record)

        # Both records should have consistent FULL policy
        assert hasattr(terminal_record, "traceback_policy")
        assert hasattr(preconfig_record, "traceback_policy")
        assert terminal_record.traceback_policy == TracebackOptions.FULL
        assert preconfig_record.traceback_policy == TracebackOptions.FULL

        # Records should have identical core data
        assert terminal_record.name == preconfig_record.name
        assert terminal_record.msg == preconfig_record.msg
        assert terminal_record.levelno == preconfig_record.levelno
        assert terminal_record.lineno == preconfig_record.lineno

        # Emit records - should not raise exceptions
        terminal_handler.emit(terminal_record)
        preconfig_handler.emit(preconfig_record)
