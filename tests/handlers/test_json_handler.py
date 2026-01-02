"""
Test JSON handler behavior including single-line output invariant and dependency handling.
"""

import io
import json
import logging
import os
import sys
from unittest.mock import patch

import pytest

from logspark.Types import MissingDependencyException, TracebackOptions


class TestJSONHandlerDependencyHandling:
    """Test JSON handler dependency management"""

    def test_json_handler_requires_dependency(self):
        """Test that JSONHandler raises MissingDependencyException when python-json-logger is unavailable"""
        # Mock missing dependency
        with patch.dict("sys.modules", {"pythonjsonlogger": None, "pythonjsonlogger.json": None}):
            with pytest.raises(MissingDependencyException) as exc_info:
                from logspark.Handlers.Json import JSONHandler

                JSONHandler()

            assert "python-json-logger" in str(exc_info.value)

    @pytest.mark.skipif(
        not pytest.importorskip("pythonjsonlogger", reason="python-json-logger not available"),
        reason="python-json-logger required for this test",
    )
    def test_json_handler_works_with_dependency(self):
        """Test that JSONHandler works correctly when python-json-logger is available"""
        from logspark.Handlers.Json import JSONHandler

        test_stream = io.StringIO()
        handler = JSONHandler(stream=test_stream)

        # Should create handler without error
        assert handler is not None
        assert hasattr(handler, "formatter")

    def test_dependency_failure_is_explicit(self):
        """Test that dependency failure is explicit and non-fatal to other handlers"""
        # Mock missing dependency by patching the import
        with patch.dict("sys.modules", {"pythonjsonlogger": None, "pythonjsonlogger.json": None}):
            # Clear any cached imports
            import importlib

            if "logspark.Handlers.Json" in sys.modules:
                importlib.reload(sys.modules["logspark.Handlers.Json"])

            # Should raise explicit exception
            with pytest.raises(MissingDependencyException):
                # Import fresh to trigger the dependency check
                import logspark.Handlers.Json

                importlib.reload(logspark.Handlers.Json)
                logspark.Handlers.Json.JSONHandler()

        # Other handlers should still work
        from logspark.Handlers.Terminal import TerminalHandler

        terminal_handler = TerminalHandler()
        assert terminal_handler is not None


@pytest.mark.skipif(
    not pytest.importorskip("pythonjsonlogger", reason="python-json-logger not available"),
    reason="python-json-logger required for JSON handler tests",
)
class TestJSONHandlerSingleLineOutput:
    """Test single-line JSON output invariant"""

    def test_single_line_output_simple_message(self):
        """Test that simple messages produce single-line JSON"""
        from logspark.Handlers.Json import JSONHandler

        test_stream = io.StringIO()
        handler = JSONHandler(stream=test_stream)

        # Create simple log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Simple test message",
            args=(),
            exc_info=None,
        )

        # Emit record
        handler.emit(record)

        # Verify single-line output
        output = test_stream.getvalue().strip()
        assert "\n" not in output, "Output should be single line"
        assert "\r" not in output, "Output should not contain carriage returns"

        # Verify it's valid JSON
        parsed = json.loads(output)
        assert parsed["message"] == "Simple test message"

    def test_single_line_output_multiline_message(self):
        """Test that multiline messages are serialized to single line"""
        from logspark.Handlers.Json import JSONHandler

        test_stream = io.StringIO()
        handler = JSONHandler(stream=test_stream)

        # Create multiline message
        multiline_message = "Line 1\nLine 2\nLine 3"
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=multiline_message,
            args=(),
            exc_info=None,
        )

        # Emit record
        handler.emit(record)

        # Verify single-line output
        output = test_stream.getvalue().strip()
        assert "\n" not in output, "Output should be single line"
        assert "\r" not in output, "Output should not contain carriage returns"

        # Verify it's valid JSON and contains the message
        parsed = json.loads(output)
        assert multiline_message in parsed["message"]

    def test_single_line_output_with_exception(self):
        """Test that exceptions are serialized to single line"""
        from logspark.Handlers.Json import JSONHandler

        test_stream = io.StringIO()
        handler = JSONHandler(stream=test_stream)

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
            raise ValueError("Test\nmultiline\nexception")
        except ValueError:
            record.exc_info = sys.exc_info()

        # Set traceback policy
        record.traceback_policy = TracebackOptions.FULL

        # Emit record
        handler.emit(record)

        # Verify single-line output
        output = test_stream.getvalue().strip()
        assert "\n" not in output, "Output should be single line even with exception"
        assert "\r" not in output, "Output should not contain carriage returns"

        # Verify it's valid JSON
        parsed = json.loads(output)
        assert "Error occurred" in parsed["message"]


@pytest.mark.skipif(
    not pytest.importorskip("pythonjsonlogger", reason="python-json-logger not available"),
    reason="python-json-logger required for JSON handler tests",
)
class TestJSONHandlerStructuredFields:
    """Test structured field presence in JSON output"""

    def test_standard_fields_present(self):
        """Test that standard logging fields are present in JSON output"""
        from logspark.Handlers.Json import JSONHandler

        test_stream = io.StringIO()
        handler = JSONHandler(stream=test_stream)

        # Create log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.WARNING,
            pathname="/path/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_function"

        # Emit record
        handler.emit(record)

        # Parse JSON output
        output = test_stream.getvalue().strip()
        parsed = json.loads(output)

        # Verify standard fields
        assert "name" in parsed
        assert "asctime" in parsed
        assert "levelname" in parsed
        assert "message" in parsed
        assert "filename" in parsed
        assert "lineno" in parsed
        assert "funcName" in parsed

        # Verify field values
        assert parsed["name"] == "test.logger"
        assert parsed["levelname"] == "WARNING"
        assert parsed["message"] == "Test message"
        assert parsed["lineno"] == 42
        assert parsed["funcName"] == "test_function"

    def test_extra_fields_included(self):
        """Test that extra fields are included in JSON output"""
        from logspark.Handlers.Json import JSONHandler

        test_stream = io.StringIO()
        handler = JSONHandler(stream=test_stream)

        # Create log record with extra fields
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Add extra fields
        record.user_id = 12345
        record.request_id = "req-abc-123"
        record.custom_field = "custom_value"

        # Emit record
        handler.emit(record)

        # Parse JSON output
        output = test_stream.getvalue().strip()
        parsed = json.loads(output)

        # Verify extra fields are included
        assert parsed["user_id"] == 12345
        assert parsed["request_id"] == "req-abc-123"
        assert parsed["custom_field"] == "custom_value"


@pytest.mark.skipif(
    not pytest.importorskip("pythonjsonlogger", reason="python-json-logger not available"),
    reason="python-json-logger required for JSON handler tests",
)
class TestJSONHandlerTracebackSerialization:
    """Test traceback serialization to single-line format"""

    def test_traceback_policy_none_excludes_exception(self):
        """Test that NONE policy excludes exception information"""
        from logspark.Handlers.Json import JSONHandler

        test_stream = io.StringIO()
        handler = JSONHandler(stream=test_stream)

        # Create record with exception
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error message",
            args=(),
            exc_info=None,
        )

        # Add exception info
        try:
            raise ValueError("Test exception")
        except ValueError:
            record.exc_info = sys.exc_info()

        # Set traceback policy to NONE
        record.traceback_policy = TracebackOptions.NONE

        # Emit record
        handler.emit(record)

        # Parse JSON output
        output = test_stream.getvalue().strip()
        parsed = json.loads(output)

        # Verify no exception information
        assert "exc_info" not in parsed
        assert "exc_text" not in parsed or parsed.get("exc_text") is None

    def test_traceback_policy_compact_single_line(self):
        """Test that COMPACT policy produces single-line traceback"""
        from logspark.Handlers.Json import JSONHandler

        test_stream = io.StringIO()
        handler = JSONHandler(stream=test_stream)

        # Create record with exception
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error message",
            args=(),
            exc_info=None,
        )

        # Add exception info
        try:
            raise ValueError("Test exception")
        except ValueError:
            record.exc_info = sys.exc_info()

        # Set traceback policy to COMPACT
        record.traceback_policy = TracebackOptions.COMPACT

        # Emit record
        handler.emit(record)

        # Verify single-line output
        output = test_stream.getvalue().strip()
        assert "\n" not in output, "Output should be single line"

        # Parse JSON output
        parsed = json.loads(output)

        # Verify compact exception information is present
        # JSON handler might use 'exc_info' field instead of 'exc_text'
        has_exception_info = ("exc_text" in parsed and parsed["exc_text"] is not None) or (
            "exc_info" in parsed and parsed["exc_info"] is not None
        )
        assert has_exception_info, "JSON output should contain exception information"

        # Check the actual exception field that exists
        exc_field = parsed.get("exc_text") or parsed.get("exc_info")
        if exc_field:
            assert "ValueError: Test exception" in exc_field
            assert "\n" not in exc_field, "Exception text should be single line"

    def test_traceback_policy_full_single_line(self):
        """Test that FULL policy produces single-line traceback"""
        from logspark.Handlers.Json import JSONHandler

        test_stream = io.StringIO()
        handler = JSONHandler(stream=test_stream)

        # Create record with exception
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error message",
            args=(),
            exc_info=None,
        )

        # Add exception info
        try:
            raise ValueError("Test exception")
        except ValueError:
            record.exc_info = sys.exc_info()

        # Set traceback policy to FULL
        record.traceback_policy = TracebackOptions.FULL

        # Emit record
        handler.emit(record)

        # Verify single-line output
        output = test_stream.getvalue().strip()
        assert "\n" not in output, "Output should be single line"

        # Parse JSON output
        parsed = json.loads(output)

        # Verify full exception information is present and single-line
        # JSON handler might use 'exc_info' field instead of 'exc_text'
        has_exception_info = ("exc_text" in parsed and parsed["exc_text"] is not None) or (
            "exc_info" in parsed and parsed["exc_info"] is not None
        )
        assert has_exception_info, "JSON output should contain exception information"

        # Check the actual exception field that exists
        exc_field = parsed.get("exc_text") or parsed.get("exc_info")
        if exc_field:
            assert "ValueError: Test exception" in exc_field
            assert "Traceback" in exc_field
            assert "\n" not in exc_field, "Exception text should be single line"


@pytest.mark.skipif(
    not pytest.importorskip("pythonjsonlogger", reason="python-json-logger not available"),
    reason="python-json-logger required for JSON handler tests",
)
class TestJSONHandlerSilencedMode:
    """Test JSON handler behavior in silenced mode"""

    def test_silenced_mode_uses_devnull(self):
        """Test that silenced mode redirects output to devnull"""
        from logspark.Handlers.Json import JSONHandler

        with patch.dict("os.environ", {"LOGSPARK_MODE": "silenced"}):
            handler = JSONHandler()

            # In silenced mode, should not write to stdout/stderr
            # The exact stream used is implementation detail, but should not be stdout/stderr
            assert handler.stream is not sys.stdout
            assert handler.stream is not sys.stderr

    def test_normal_mode_uses_stdout(self):
        """Test that normal mode uses stdout by default"""
        from logspark.Handlers.Json import JSONHandler

        with patch.dict("os.environ", {}, clear=False):
            if "LOGSPARK_MODE" in os.environ:
                del os.environ["LOGSPARK_MODE"]

            handler = JSONHandler()

            # Should use stdout by default
            assert handler.stream is sys.stdout


# Property-Based Tests
from hypothesis import given
from hypothesis import strategies as st


@pytest.mark.skipif(
    not pytest.importorskip("pythonjsonlogger", reason="python-json-logger not available"),
    reason="python-json-logger required for JSON handler property tests",
)
class TestJSONHandlerProperties:
    """Property-based tests for JSON handler behavior"""

    @given(
        message=st.text(min_size=0, max_size=1000),
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
    def test_property_json_single_line_output(self, message, level, logger_name, lineno):
        """
        JSON Single-Line Output
        For any log message, level, logger name, and line number, JSON output should be single-line
        """
        from logspark.Handlers.Json import JSONHandler

        test_stream = io.StringIO()
        handler = JSONHandler(stream=test_stream)

        # Create log record
        record = logging.LogRecord(
            name=logger_name,
            level=level,
            pathname="test.py",
            lineno=lineno,
            msg=message,
            args=(),
            exc_info=None,
        )

        # Emit record
        handler.emit(record)

        # Verify single-line output
        output = test_stream.getvalue().strip()
        assert "\n" not in output, f"Output should be single line, got: {repr(output)}"
        assert "\r" not in output, (
            f"Output should not contain carriage returns, got: {repr(output)}"
        )

        # Verify it's valid JSON
        if output:  # Only parse if there's output
            parsed = json.loads(output)
            assert isinstance(parsed, dict), "Output should be a JSON object"

            # Verify message is preserved (if not empty)
            if message.strip():
                assert "message" in parsed
                assert message in parsed["message"]

    @given(
        message=st.text(min_size=1, max_size=500),
        exception_message=st.text(min_size=1, max_size=200),
        traceback_policy=st.sampled_from([
            TracebackOptions.NONE,
            TracebackOptions.COMPACT,
            TracebackOptions.FULL,
        ]),
    )
    def test_property_json_traceback_serialization(
        self, message, exception_message, traceback_policy
    ):
        """
        For any message and exception, traceback should be serialized to single-line format
        """
        from logspark.Handlers.Json import JSONHandler

        test_stream = io.StringIO()
        handler = JSONHandler(stream=test_stream)

        # Create record with exception
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg=message,
            args=(),
            exc_info=None,
        )

        # Add exception info
        try:
            raise ValueError(exception_message)
        except ValueError:
            record.exc_info = sys.exc_info()

        # Set traceback policy
        record.traceback_policy = traceback_policy

        # Emit record
        handler.emit(record)

        # Verify single-line output
        output = test_stream.getvalue().strip()
        assert "\n" not in output, (
            f"Output should be single line even with exception, got: {repr(output)}"
        )
        assert "\r" not in output, (
            f"Output should not contain carriage returns, got: {repr(output)}"
        )

        # Verify it's valid JSON
        parsed = json.loads(output)
        assert isinstance(parsed, dict), "Output should be a JSON object"

        # Verify traceback policy was applied
        if traceback_policy == TracebackOptions.NONE:
            # Should not have exception information
            assert parsed.get("exc_text") is None or parsed.get("exc_text") == ""
        else:
            # Should have exception information in single-line format
            if "exc_text" in parsed and parsed["exc_text"]:
                exc_text = parsed["exc_text"]
                assert "\n" not in exc_text, (
                    f"Exception text should be single line, got: {repr(exc_text)}"
                )
                assert "\r" not in exc_text, (
                    f"Exception text should not contain carriage returns, got: {repr(exc_text)}"
                )

                # Should contain exception information
                assert "ValueError" in exc_text
                if exception_message.strip():
                    assert exception_message in exc_text

    @given(
        message=st.text(min_size=1, max_size=500),
        extra_fields=st.dictionaries(
            keys=st.text(
                min_size=2,
                max_size=50,
                alphabet=st.characters(
                    whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_"
                ),
            ).filter(
                lambda x: not x.startswith("_")
                and x
                not in [
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "message",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "asctime",
                ]
            ),
            values=st.one_of(
                st.text(max_size=100),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.booleans(),
            ),
            min_size=0,
            max_size=5,
        ),
    )
    def test_property_json_structured_fields(self, message, extra_fields):
        """
        For any message and extra fields, all fields should be present in JSON output
        """
        from logspark.Handlers.Json import JSONHandler

        test_stream = io.StringIO()
        handler = JSONHandler(stream=test_stream)

        # Create log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=message,
            args=(),
            exc_info=None,
        )

        # Add extra fields to record
        for key, value in extra_fields.items():
            setattr(record, key, value)

        # Emit record
        handler.emit(record)

        # Verify output
        output = test_stream.getvalue().strip()
        if output:  # Only parse if there's output
            parsed = json.loads(output)

            # Verify standard fields are present
            assert "message" in parsed
            assert "name" in parsed
            assert "levelname" in parsed

            # Verify extra fields are included
            for key, expected_value in extra_fields.items():
                assert key in parsed, f"Extra field '{key}' should be in output"
                assert parsed[key] == expected_value, (
                    f"Extra field '{key}' should have value {expected_value}"
                )

    def test_property_json_handler_dependency(self):
        """
        When python-json-logger is present, structured output should be provided,
        when absent, MissingDependencyException should be raised
        """
        # Test with dependency present (current environment)
        try:
            import pythonjsonlogger  # noqa: F401

            dependency_available = True
        except ImportError:
            dependency_available = False

        if dependency_available:
            # Should work when dependency is available
            from logspark.Handlers.Json import JSONHandler

            handler = JSONHandler()
            assert handler is not None

        # Test with dependency absent (mocked)
        with patch.dict("sys.modules", {"pythonjsonlogger": None, "pythonjsonlogger.json": None}):
            with pytest.raises(MissingDependencyException) as exc_info:
                from logspark.Handlers.Json import JSONHandler

                JSONHandler()

            # Verify the exception mentions the missing dependency
            assert "python-json-logger" in str(exc_info.value)


@pytest.mark.skipif(
    not pytest.importorskip("pythonjsonlogger", reason="python-json-logger not available"),
    reason="python-json-logger required for JSON handler tests",
)
class TestJSONSingleLineConsistency:
    """Test JSON single-line output consistency across various inputs"""

    def test_json_single_line_with_nested_exception(self):
        """Test JSON output is single line with nested exceptions"""
        from logspark.Handlers.Json import JSONHandler

        test_stream = io.StringIO()
        handler = JSONHandler(stream=test_stream)

        # Create record with nested exception
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Nested error occurred",
            args=(),
            exc_info=None,
        )

        # Add nested exception info
        try:
            try:
                raise ValueError("Inner exception")
            except ValueError as e:
                raise RuntimeError("Outer exception") from e
        except RuntimeError:
            record.exc_info = sys.exc_info()

        # Set traceback policy
        record.traceback_policy = TracebackOptions.FULL

        # Emit record
        handler.emit(record)

        # Verify single-line output
        output = test_stream.getvalue().strip()
        assert "\n" not in output, "Output should be single line"
        assert "\r" not in output, "Output should not contain carriage returns"

        # Verify it's valid JSON
        parsed = json.loads(output)
        assert "Nested error occurred" in parsed["message"]

        # Should contain exception information in single-line format
        if "exc_text" in parsed or "exc_info" in parsed:
            exc_field = parsed.get("exc_text") or parsed.get("exc_info")
            if exc_field:
                assert "RuntimeError: Outer exception" in exc_field
                assert "\n" not in exc_field, "Exception text should be single line"

    def test_json_single_line_with_multiline_message(self):
        """Test JSON output is single line even with multiline log messages"""
        from logspark.Handlers.Json import JSONHandler

        test_stream = io.StringIO()
        handler = JSONHandler(stream=test_stream)

        # Create record with multiline message
        multiline_message = "Line 1\nLine 2\nLine 3"
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=multiline_message,
            args=(),
            exc_info=None,
        )

        # Set traceback policy
        record.traceback_policy = TracebackOptions.NONE

        # Emit record
        handler.emit(record)

        # Verify single-line output
        output = test_stream.getvalue().strip()
        assert "\n" not in output, "Output should be single line"
        assert "\r" not in output, "Output should not contain carriage returns"

        # Verify it's valid JSON and message is preserved
        parsed = json.loads(output)
        # The message should be preserved in some form (possibly with separators)
        assert "Line 1" in parsed["message"] or "|" in parsed["message"]

    def test_json_multiple_messages_single_line(self):
        """Test that multiple JSON messages each produce single lines"""
        from logspark.Handlers.Json import JSONHandler

        test_stream = io.StringIO()
        handler = JSONHandler(stream=test_stream)

        messages = ["Message 1", "Message 2", "Message 3"]

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
            record.traceback_policy = TracebackOptions.NONE
            handler.emit(record)

        output = test_stream.getvalue()

        if output.strip():
            lines = output.strip().split("\n")

            # Each line should be valid single-line JSON
            for line_num, line in enumerate(lines):
                if line.strip():  # Skip empty lines
                    # Must not contain additional newlines
                    assert "\n" not in line, f"Line {line_num} contains newlines: {repr(line)}"
                    assert "\r" not in line, (
                        f"Line {line_num} contains carriage returns: {repr(line)}"
                    )

                    # Must be valid JSON
                    parsed = json.loads(line)
                    assert "message" in parsed
                    assert "levelname" in parsed
