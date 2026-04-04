"""
Test DDTrace correlation filter behavior.

This module tests the DDTraceInjectionFilter to ensure it correctly
injects correlation fields when DDTrace is present, handles absence gracefully,
and maintains failure resilience.
"""

import logging
from unittest.mock import MagicMock, patch

from logspark.Filters.DDTraceInjectionFilter import DDTraceInjectionFilter


class TestDDTraceCorrelationPresent:
    """Test correlation field injection when DDTrace present"""

    def test_correlation_injection_with_active_span(self):
        """Test that correlation fields are injected when DDTrace has an active span"""
        # Mock DDTrace tracer with active span
        mock_span = MagicMock()
        mock_span.trace_id = 12345678901234567890
        mock_span.span_id = 9876543210987654321

        mock_tracer = MagicMock()
        mock_tracer.current_span.return_value = mock_span

        # Patch the module-level tracer
        with patch("logspark.Filters.DDTraceInjectionFilter._dd_tracer", mock_tracer):
            filter_obj = DDTraceInjectionFilter()

            record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="test.py",
                lineno=42,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            # Filter should return True and inject correlation fields
            result = filter_obj.filter(record)
            assert result is True

            # Verify correlation fields were injected
            assert hasattr(record, "dd_trace_id")
            assert hasattr(record, "dd_span_id")
            assert record.dd_trace_id == 12345678901234567890
            assert record.dd_span_id == 9876543210987654321

    def test_correlation_no_injection_without_active_span(self):
        """Test that no correlation fields are injected when DDTrace has no active span"""
        mock_tracer = MagicMock()
        mock_tracer.current_span.return_value = None

        with patch("logspark.Filters.DDTraceInjectionFilter._dd_tracer", mock_tracer):
            filter_obj = DDTraceInjectionFilter()

            record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="test.py",
                lineno=42,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            # Filter should return True but not inject correlation fields
            result = filter_obj.filter(record)
            assert result is True

            # Verify no correlation fields were injected
            assert not hasattr(record, "dd_trace_id")
            assert not hasattr(record, "dd_span_id")

    def test_original_log_content_unchanged(self):
        """Test that DDTrace correlation doesn't affect original log content"""
        mock_span = MagicMock()
        mock_span.trace_id = 12345678901234567890
        mock_span.span_id = 9876543210987654321

        mock_tracer = MagicMock()
        mock_tracer.current_span.return_value = mock_span

        with patch("logspark.Filters.DDTraceInjectionFilter._dd_tracer", mock_tracer):
            filter_obj = DDTraceInjectionFilter()

            record = logging.LogRecord(
                name="test.logger",
                level=logging.WARNING,
                pathname="test.py",
                lineno=42,
                msg="Important warning message",
                args=(),
                exc_info=None,
            )

            # Store original values
            original_name = record.name
            original_level = record.levelno
            original_msg = record.msg
            original_pathname = record.pathname
            original_lineno = record.lineno

            # Apply filter
            result = filter_obj.filter(record)
            assert result is True

            # Verify original content is unchanged
            assert record.name == original_name
            assert record.levelno == original_level
            assert record.msg == original_msg
            assert record.pathname == original_pathname
            assert record.lineno == original_lineno

            # But correlation fields should be added
            assert hasattr(record, "dd_trace_id")
            assert hasattr(record, "dd_span_id")


class TestDDTraceCorrelationAbsent:
    """Test normal logging when DDTrace absent"""

    def test_normal_logging_when_ddtrace_absent(self):
        """Test that logging proceeds normally when DDTrace is not available"""
        # Patch to simulate DDTrace not being available
        with patch("logspark.Filters.DDTraceInjectionFilter._dd_tracer", None):
            filter_obj = DDTraceInjectionFilter()

            record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="test.py",
                lineno=42,
                msg="Test message without DDTrace",
                args=(),
                exc_info=None,
            )

            # Filter should return True and not inject any fields
            result = filter_obj.filter(record)
            assert result is True

            # Verify no correlation fields were injected
            assert not hasattr(record, "dd_trace_id")
            assert not hasattr(record, "dd_span_id")

            # Original record should be unchanged
            assert record.name == "test.logger"
            assert record.msg == "Test message without DDTrace"

    def test_multiple_records_without_ddtrace(self):
        """Test that multiple records are processed correctly without DDTrace"""
        with patch("logspark.Filters.DDTraceInjectionFilter._dd_tracer", None):
            filter_obj = DDTraceInjectionFilter()

            records = [
                logging.LogRecord("logger1", logging.DEBUG, "test1.py", 1, "debug", (), None),
                logging.LogRecord("logger2", logging.INFO, "test2.py", 2, "info", (), None),
                logging.LogRecord("logger3", logging.ERROR, "test3.py", 3, "error", (), None),
            ]

            for record in records:
                result = filter_obj.filter(record)
                assert result is True
                assert not hasattr(record, "dd_trace_id")
                assert not hasattr(record, "dd_span_id")


class TestDDTraceFailureResilience:
    """Test failure resilience (logging continues on DDTrace errors)"""

    def test_logging_continues_on_ddtrace_exception(self):
        """Test that logging continues when DDTrace operations raise exceptions"""
        mock_tracer = MagicMock()
        mock_tracer.current_span.side_effect = Exception("DDTrace error")

        with patch("logspark.Filters.DDTraceInjectionFilter._dd_tracer", mock_tracer):
            filter_obj = DDTraceInjectionFilter()

            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=42,
                msg="Error message",
                args=(),
                exc_info=None,
            )

            # Filter should return True despite DDTrace exception
            result = filter_obj.filter(record)
            assert result is True

            # No correlation fields should be injected due to exception
            assert not hasattr(record, "dd_trace_id")
            assert not hasattr(record, "dd_span_id")

            # Original record should be unchanged
            assert record.name == "test.logger"
            assert record.msg == "Error message"

    def test_logging_continues_on_span_attribute_error(self):
        """Test that logging continues when span attributes are not accessible"""

        # Create a mock span that raises AttributeError when accessing trace_id
        class FailingSpan:
            @property
            def trace_id(self):
                raise AttributeError("No trace_id")

            @property
            def span_id(self):
                raise AttributeError("No span_id")

        mock_tracer = MagicMock()
        mock_tracer.current_span.return_value = FailingSpan()

        with patch("logspark.Filters.DDTraceInjectionFilter._dd_tracer", mock_tracer):
            filter_obj = DDTraceInjectionFilter()

            record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="test.py",
                lineno=42,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            # Filter should return True despite attribute error
            result = filter_obj.filter(record)
            assert result is True

            # No correlation fields should be injected due to exception
            assert not hasattr(record, "dd_trace_id")
            assert not hasattr(record, "dd_span_id")

    def test_filter_always_returns_true(self):
        """Test that DDTrace filter always allows records to pass through"""
        # Test with various scenarios
        scenarios = [
            # DDTrace available with active span
            (MagicMock(), lambda t: setattr(t, "current_span", lambda: MagicMock())),
            # DDTrace available but no active span
            (MagicMock(), lambda t: setattr(t, "current_span", lambda: None)),
            # DDTrace not available
            (None, lambda t: None),
        ]

        for tracer, setup in scenarios:
            if setup and tracer:
                setup(tracer)

            with patch("logspark.Filters.DDTraceInjectionFilter._dd_tracer", tracer):
                filter_obj = DDTraceInjectionFilter()

                record = logging.LogRecord(
                    name="test.logger",
                    level=logging.INFO,
                    pathname="test.py",
                    lineno=42,
                    msg="Test message",
                    args=(),
                    exc_info=None,
                )

                result = filter_obj.filter(record)
                assert result is True, (
                    f"Filter should always return True for scenario with tracer: {tracer}"
                )


# Import PropertyMock for the attribute error test

# Property-based tests
from hypothesis import given
from hypothesis import strategies as st


class TestDDTraceCorrelationProperties:
    """Property-based tests for DDTrace correlation filter behavior"""

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
        trace_id=st.integers(min_value=1, max_value=2**63 - 1),
        span_id=st.integers(min_value=1, max_value=2**63 - 1),
    )
    def test_property_ddtrace_correlation_injection(
        self, logger_name, message, level, lineno, trace_id, span_id
    ):
        """

        For any log record, when DDTrace is present with active span, correlation fields should be injected

        """
        # Mock DDTrace tracer with active span
        mock_span = MagicMock()
        mock_span.trace_id = trace_id
        mock_span.span_id = span_id

        mock_tracer = MagicMock()
        mock_tracer.current_span.return_value = mock_span

        with patch("logspark.Filters.DDTraceInjectionFilter._dd_tracer", mock_tracer):
            filter_obj = DDTraceInjectionFilter()

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

            # Apply filter
            result = filter_obj.filter(record)

            # Filter should always return True
            assert result is True

            # Correlation fields should be injected
            assert hasattr(record, "dd_trace_id")
            assert hasattr(record, "dd_span_id")
            assert record.dd_trace_id == trace_id
            assert record.dd_span_id == span_id

            # Original log content should be unchanged
            assert record.name == original_name
            assert record.msg == original_msg
            assert record.levelno == original_level
            assert record.lineno == original_lineno

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
    )
    def test_property_ddtrace_absence_handling(self, logger_name, message, level, lineno):
        """

        For any log record, when DDTrace is absent, logging should proceed normally without correlation fields

        """
        # Simulate DDTrace not being available
        with patch("logspark.Filters.DDTraceInjectionFilter._dd_tracer", None):
            filter_obj = DDTraceInjectionFilter()

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

            # Apply filter
            result = filter_obj.filter(record)

            # Filter should always return True
            assert result is True

            # No correlation fields should be injected
            assert not hasattr(record, "dd_trace_id")
            assert not hasattr(record, "dd_span_id")

            # Original log content should be unchanged
            assert record.name == original_name
            assert record.msg == original_msg
            assert record.levelno == original_level
            assert record.lineno == original_lineno

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
        error_type=st.sampled_from([Exception, AttributeError, RuntimeError, ValueError]),
    )
    def test_property_ddtrace_failure_resilience(
        self, logger_name, message, level, lineno, error_type
    ):
        """

        For any DDTrace correlation failure, logging should continue without blocking

        """
        # Mock DDTrace tracer that raises exceptions
        mock_tracer = MagicMock()
        mock_tracer.current_span.side_effect = error_type("Simulated DDTrace error")

        with patch("logspark.Filters.DDTraceInjectionFilter._dd_tracer", mock_tracer):
            filter_obj = DDTraceInjectionFilter()

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

            # Apply filter - should not raise exception
            result = filter_obj.filter(record)

            # Filter should always return True even on DDTrace errors
            assert result is True

            # No correlation fields should be injected due to error
            assert not hasattr(record, "dd_trace_id")
            assert not hasattr(record, "dd_span_id")

            # Original log content should be unchanged
            assert record.name == original_name
            assert record.msg == original_msg
            assert record.levelno == original_level
            assert record.lineno == original_lineno
