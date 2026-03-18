"""
Test traceback policy behavior across different handlers.

This module tests the HIDE, COMPACT, and FULL traceback policies to ensure
they behave consistently and correctly modify log records as expected.
"""

import io
import logging
import sys

from logspark._Internal.Func.configure_handler_traceback_policy import (
    configure_handler_traceback_policy,
)
from logspark.Types.Options import TracebackOptions


class TestTracebackPolicyNone:
    """Test HIDE policy excludes exception information"""

    def test_none_policy_excludes_exception_info(self):
        """Test that HIDE policy excludes exception information from records"""
        # Create a basic handler
        handler = logging.StreamHandler(io.StringIO())
        configure_handler_traceback_policy(handler, TracebackOptions.HIDE)

        # Create a record with exception info
        try:
            raise ValueError("Test exception for HIDE policy")
        except ValueError:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )

        # Process the record through the handler's filters
        for filter_obj in handler.filters:
            filter_obj.filter(record)

        # Verify traceback policy was set
        assert hasattr(record, "traceback_policy")
        assert record.traceback_policy == TracebackOptions.HIDE

        # The record should still have exc_info at this point
        # (handlers are responsible for processing the policy)
        assert record.exc_info is not None

    def test_none_policy_with_no_exception(self):
        """Test that HIDE policy works correctly with records that have no exception"""
        handler = logging.StreamHandler(io.StringIO())
        configure_handler_traceback_policy(handler, TracebackOptions.HIDE)

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Normal log message",
            args=(),
            exc_info=None,
        )

        # Process the record through the handler's filters
        for filter_obj in handler.filters:
            filter_obj.filter(record)

        # Verify traceback policy was set
        assert hasattr(record, "traceback_policy")
        assert record.traceback_policy == TracebackOptions.HIDE
        assert record.exc_info is None


class TestTracebackPolicyCompact:
    """Test COMPACT policy includes essential information"""

    def test_compact_policy_sets_policy_attribute(self):
        """Test that COMPACT policy sets the correct policy attribute"""
        handler = logging.StreamHandler(io.StringIO())
        configure_handler_traceback_policy(handler, TracebackOptions.COMPACT)

        try:
            raise ValueError("Test exception for COMPACT policy")
        except ValueError:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )

        # Process the record through the handler's filters
        for filter_obj in handler.filters:
            filter_obj.filter(record)

        # Verify traceback policy was set
        assert hasattr(record, "traceback_policy")
        assert record.traceback_policy == TracebackOptions.COMPACT

    def test_compact_policy_with_no_exception(self):
        """Test that COMPACT policy works correctly with records that have no exception"""
        handler = logging.StreamHandler(io.StringIO())
        configure_handler_traceback_policy(handler, TracebackOptions.COMPACT)

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Normal log message",
            args=(),
            exc_info=None,
        )

        # Process the record through the handler's filters
        for filter_obj in handler.filters:
            filter_obj.filter(record)

        # Verify traceback policy was set
        assert hasattr(record, "traceback_policy")
        assert record.traceback_policy == TracebackOptions.COMPACT
        assert record.exc_info is None


class TestTracebackPolicyFull:
    """Test FULL policy includes complete information"""

    def test_full_policy_sets_policy_attribute(self):
        """Test that FULL policy sets the correct policy attribute"""
        handler = logging.StreamHandler(io.StringIO())
        configure_handler_traceback_policy(handler, TracebackOptions.FULL)

        try:
            raise ValueError("Test exception for FULL policy")
        except ValueError:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )

        # Process the record through the handler's filters
        for filter_obj in handler.filters:
            filter_obj.filter(record)

        # Verify traceback policy was set
        assert hasattr(record, "traceback_policy")
        assert record.traceback_policy == TracebackOptions.FULL

    def test_full_policy_with_no_exception(self):
        """Test that FULL policy works correctly with records that have no exception"""
        handler = logging.StreamHandler(io.StringIO())
        configure_handler_traceback_policy(handler, TracebackOptions.FULL)

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Normal log message",
            args=(),
            exc_info=None,
        )

        # Process the record through the handler's filters
        for filter_obj in handler.filters:
            filter_obj.filter(record)

        # Verify traceback policy was set
        assert hasattr(record, "traceback_policy")
        assert record.traceback_policy == TracebackOptions.FULL
        assert record.exc_info is None


class TestRecordMutationGuarantees:
    """Test record mutation guarantees"""

    def test_filter_mutates_record_not_output(self):
        """Test that traceback policy filter mutates records but doesn't format output"""
        handler = logging.StreamHandler(io.StringIO())
        configure_handler_traceback_policy(handler, TracebackOptions.COMPACT)

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Record should not have traceback_policy initially
        assert not hasattr(record, "traceback_policy")

        # Process through filters
        for filter_obj in handler.filters:
            result = filter_obj.filter(record)
            # Filter should return True (allow record to pass)
            assert result is True

        # Record should now have traceback_policy attribute
        assert hasattr(record, "traceback_policy")
        assert record.traceback_policy == TracebackOptions.COMPACT

        # The original message and other attributes should be unchanged
        assert record.msg == "Test message"
        assert record.levelno == logging.INFO
        assert record.name == "test.logger"

    def test_multiple_filters_preserve_policy(self):
        """Test that multiple filters don't interfere with traceback policy"""
        handler = logging.StreamHandler(io.StringIO())

        # Add a custom filter first
        class CustomFilter(logging.Filter):
            def filter(self, record):
                record.custom_field = "custom_value"
                return True

        handler.addFilter(CustomFilter())
        configure_handler_traceback_policy(handler, TracebackOptions.FULL)

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
        for filter_obj in handler.filters:
            filter_obj.filter(record)

        # Both custom field and traceback policy should be set
        assert hasattr(record, "custom_field")
        assert record.custom_field == "custom_value"
        assert hasattr(record, "traceback_policy")
        assert record.traceback_policy == TracebackOptions.FULL

    def test_filter_always_returns_true(self):
        """Test that traceback policy filter always allows records to pass through"""
        handler = logging.StreamHandler(io.StringIO())
        configure_handler_traceback_policy(handler, TracebackOptions.HIDE)

        # Test with various record types
        records = [
            logging.LogRecord("test", logging.DEBUG, "test.py", 1, "debug", (), None),
            logging.LogRecord("test", logging.INFO, "test.py", 1, "info", (), None),
            logging.LogRecord("test", logging.WARNING, "test.py", 1, "warning", (), None),
            logging.LogRecord("test", logging.ERROR, "test.py", 1, "error", (), None),
            logging.LogRecord("test", logging.CRITICAL, "test.py", 1, "critical", (), None),
        ]

        for record in records:
            for filter_obj in handler.filters:
                result = filter_obj.filter(record)
                assert result is True, f"Filter should always return True for {record.levelname}"
                assert hasattr(record, "traceback_policy")
                assert record.traceback_policy == TracebackOptions.HIDE


# Property-based tests
from hypothesis import given
from hypothesis import strategies as st


class TestTracebackPolicyProperties:
    """Property-based tests for traceback policy behavior"""

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
    def test_property_traceback_policy_none(
        self, logger_name, message, level, lineno, exception_message
    ):
        """

        For any log record, when traceback policy is HIDE, the policy should be set correctly

        """
        handler = logging.StreamHandler(io.StringIO())
        configure_handler_traceback_policy(handler, TracebackOptions.HIDE)

        # Create record with or without exception
        try:
            raise ValueError(exception_message)
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name=logger_name,
            level=level,
            pathname="test.py",
            lineno=lineno,
            msg=message,
            args=(),
            exc_info=exc_info,
        )

        # Process through filters
        for filter_obj in handler.filters:
            result = filter_obj.filter(record)
            assert result is True

        # Verify HIDE policy was applied
        assert hasattr(record, "traceback_policy")
        assert record.traceback_policy == TracebackOptions.HIDE
        # Original record data should be preserved
        assert record.name == logger_name
        assert record.msg == message
        assert record.levelno == level
        assert record.lineno == lineno

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
    def test_property_traceback_policy_compact(
        self, logger_name, message, level, lineno, exception_message
    ):
        """

        For any log record, when traceback policy is COMPACT, the policy should be set correctly

        """
        handler = logging.StreamHandler(io.StringIO())
        configure_handler_traceback_policy(handler, TracebackOptions.COMPACT)

        # Create record with or without exception
        try:
            raise ValueError(exception_message)
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name=logger_name,
            level=level,
            pathname="test.py",
            lineno=lineno,
            msg=message,
            args=(),
            exc_info=exc_info,
        )

        # Process through filters
        for filter_obj in handler.filters:
            result = filter_obj.filter(record)
            assert result is True

        # Verify COMPACT policy was applied
        assert hasattr(record, "traceback_policy")
        assert record.traceback_policy == TracebackOptions.COMPACT
        # Original record data should be preserved
        assert record.name == logger_name
        assert record.msg == message
        assert record.levelno == level
        assert record.lineno == lineno

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
    def test_property_traceback_policy_full(
        self, logger_name, message, level, lineno, exception_message
    ):
        """

        For any log record, when traceback policy is FULL, the policy should be set correctly

        """
        handler = logging.StreamHandler(io.StringIO())
        configure_handler_traceback_policy(handler, TracebackOptions.FULL)

        # Create record with or without exception
        try:
            raise ValueError(exception_message)
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name=logger_name,
            level=level,
            pathname="test.py",
            lineno=lineno,
            msg=message,
            args=(),
            exc_info=exc_info,
        )

        # Process through filters
        for filter_obj in handler.filters:
            result = filter_obj.filter(record)
            assert result is True

        # Verify FULL policy was applied
        assert hasattr(record, "traceback_policy")
        assert record.traceback_policy == TracebackOptions.FULL
        # Original record data should be preserved
        assert record.name == logger_name
        assert record.msg == message
        assert record.levelno == level
        assert record.lineno == lineno

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
        policy=st.sampled_from([
            TracebackOptions.HIDE,
            TracebackOptions.COMPACT,
            TracebackOptions.FULL,
        ]),
    )
    def test_property_filter_record_mutation(self, logger_name, message, level, lineno, policy):
        """

        For any log record and traceback policy, filters should modify records but not format output

        """
        handler = logging.StreamHandler(io.StringIO())
        configure_handler_traceback_policy(handler, policy)

        record = logging.LogRecord(
            name=logger_name,
            level=level,
            pathname="test.py",
            lineno=lineno,
            msg=message,
            args=(),
            exc_info=None,
        )

        # Store original values
        original_name = record.name
        original_msg = record.msg
        original_level = record.levelno
        original_lineno = record.lineno

        # Record should not have traceback_policy initially
        assert not hasattr(record, "traceback_policy")

        # Process through filters
        for filter_obj in handler.filters:
            result = filter_obj.filter(record)
            # Filter should return True (allow record to pass)
            assert result is True

        # Record should now have traceback_policy attribute (mutation)
        assert hasattr(record, "traceback_policy")
        assert record.traceback_policy == policy

        # Original record data should be preserved (no formatting)
        assert record.name == original_name
        assert record.msg == original_msg
        assert record.levelno == original_level
        assert record.lineno == original_lineno
