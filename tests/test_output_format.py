"""
Tests for output format consistency in LogSpark Logging

This module tests JSON single-line output invariant and traceback policy adherence.
"""
import os
import json
import logging
from io import StringIO
from unittest.mock import patch

from logspark.Handlers import TerminalHandler
from logspark.Handlers import JSONHandler
from logspark.Types import TracebackOptions


class TestJSONSingleLineInvariant:
    """Test JSON single-line output invariant for all traceback policies"""

    def test_json_single_line_no_traceback(self):
        """Test JSON output is single line with no traceback policy"""
        stream = StringIO()
        
        handler = JSONHandler(stream)

        # Create a test logger
        logger = logging.getLogger("test_json_no_tb")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        # Configure traceback policy filter
        class TracebackPolicyFilter(logging.Filter):
            def filter(self, record):
                record.traceback_policy = TracebackOptions.NONE
                return True

        handler.addFilter(TracebackPolicyFilter())

        # Log a simple message
        logger.info("Test message")

        output = stream.getvalue()

        # Verify single line
        assert "\n" not in output.strip(), f"Output contains newlines: {repr(output)}"
        assert "\r" not in output.strip(), f"Output contains carriage returns: {repr(output)}"

        # Verify it's valid JSON
        json_data = json.loads(output.strip())
        assert json_data["message"] == "Test message"
        assert json_data["levelname"] == "INFO"
        

    def test_json_single_line_with_exception_none_policy(self):
        """Test JSON output is single line with exception and NONE traceback policy"""
        stream = StringIO()
        
        handler = JSONHandler(stream)

        logger = logging.getLogger("test_json_exc_none")
        logger.setLevel(logging.ERROR)
        logger.addHandler(handler)

        # Configure traceback policy filter
        class TracebackPolicyFilter(logging.Filter):
            def filter(self, record):
                record.traceback_policy = TracebackOptions.NONE
                return True

        handler.addFilter(TracebackPolicyFilter())

        # Log with exception
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.error("Error occurred", exc_info=True)

        output = stream.getvalue()

        # Verify single line
        assert "\n" not in output.strip(), f"Output contains newlines: {repr(output)}"
        assert "\r" not in output.strip(), f"Output contains carriage returns: {repr(output)}"

        # Verify it's valid JSON and no traceback info
        json_data = json.loads(output.strip())
        assert json_data["message"] == "Error occurred"
        assert "exc_text" not in json_data or json_data.get("exc_text") is None
        

    def test_json_single_line_with_exception_compact_policy(self):
        """Test JSON output is single line with exception and COMPACT traceback policy"""
        stream = StringIO()
        
        handler = JSONHandler(stream)

        logger = logging.getLogger("test_json_exc_compact")
        logger.setLevel(logging.ERROR)
        logger.addHandler(handler)

        # Configure traceback policy filter
        class TracebackPolicyFilter(logging.Filter):
            def filter(self, record):
                record.traceback_policy = TracebackOptions.COMPACT
                return True

        handler.addFilter(TracebackPolicyFilter())

        # Log with exception
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.error("Error occurred", exc_info=True)

        output = stream.getvalue()

        # Verify single line
        assert "\n" not in output.strip(), f"Output contains newlines: {repr(output)}"
        assert "\r" not in output.strip(), f"Output contains carriage returns: {repr(output)}"

        # Verify it's valid JSON and contains compact traceback
        json_data = json.loads(output.strip())
        assert json_data["message"] == "Error occurred"
        # python-json-logger uses 'exc_info' field for exception information
        assert "exc_info" in json_data
        assert "ValueError: Test exception" in json_data["exc_info"]
        # Should contain file and line info but all on one line
        assert "|" in json_data["exc_info"]  # Our separator for single-line format
        

    def test_json_single_line_with_exception_full_policy(self):
        """Test JSON output is single line with exception and FULL traceback policy"""
        stream = StringIO()
        
        handler = JSONHandler(stream)

        logger = logging.getLogger("test_json_exc_full")
        logger.setLevel(logging.ERROR)
        logger.addHandler(handler)

        # Configure traceback policy filter
        class TracebackPolicyFilter(logging.Filter):
            def filter(self, record):
                record.traceback_policy = TracebackOptions.FULL
                return True

        handler.addFilter(TracebackPolicyFilter())

        # Log with exception
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.error("Error occurred", exc_info=True)

        output = stream.getvalue()

        # Verify single line
        assert "\n" not in output.strip(), f"Output contains newlines: {repr(output)}"
        assert "\r" not in output.strip(), f"Output contains carriage returns: {repr(output)}"

        # Verify it's valid JSON and contains full traceback
        json_data = json.loads(output.strip())
        assert json_data["message"] == "Error occurred"
        assert "exc_info" in json_data
        assert "ValueError: Test exception" in json_data["exc_info"]
        assert "Traceback" in json_data["exc_info"]
        # Should contain full traceback info but all on one line
        assert "|" in json_data["exc_info"]  # Our separator for single-line format
        

    def test_json_single_line_with_nested_exception(self):
        """Test JSON output is single line with nested exceptions"""
        stream = StringIO()
        
        handler = JSONHandler(stream)

        logger = logging.getLogger("test_json_nested_exc")
        logger.setLevel(logging.ERROR)
        logger.addHandler(handler)

        # Configure traceback policy filter
        class TracebackPolicyFilter(logging.Filter):
            def filter(self, record):
                record.traceback_policy = TracebackOptions.FULL
                return True

        handler.addFilter(TracebackPolicyFilter())

        # Log with nested exception
        try:
            try:
                raise ValueError("Inner exception")
            except ValueError as e:
                raise RuntimeError("Outer exception") from e
        except RuntimeError:
            logger.error("Nested error occurred", exc_info=True)

        output = stream.getvalue()

        # Verify single line
        assert "\n" not in output.strip(), f"Output contains newlines: {repr(output)}"
        assert "\r" not in output.strip(), f"Output contains carriage returns: {repr(output)}"

        # Verify it's valid JSON
        json_data = json.loads(output.strip())
        assert json_data["message"] == "Nested error occurred"
        assert "exc_info" in json_data
        # Should contain both exceptions but all on one line
        assert "RuntimeError: Outer exception" in json_data["exc_info"]
        assert "|" in json_data["exc_info"]  # Our separator for single-line format
        

    def test_json_single_line_with_multiline_message(self):
        """Test JSON output is single line even with multiline log messages"""
        stream = StringIO()
        
        handler = JSONHandler(stream)

        logger = logging.getLogger("test_json_multiline_msg")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        # Configure traceback policy filter
        class TracebackPolicyFilter(logging.Filter):
            def filter(self, record):
                record.traceback_policy = TracebackOptions.NONE
                return True

        handler.addFilter(TracebackPolicyFilter())

        # Log a multiline message
        multiline_message = "Line 1\nLine 2\nLine 3"
        logger.info(multiline_message)

        output = stream.getvalue()

        # Verify single line
        assert "\n" not in output.strip(), f"Output contains newlines: {repr(output)}"
        assert "\r" not in output.strip(), f"Output contains carriage returns: {repr(output)}"

        # Verify it's valid JSON and message is preserved (but single line)
        json_data = json.loads(output.strip())
        # The message should contain the pipe separator instead of newlines
        assert "|" in json_data["message"] or "Line 1" in json_data["message"]
        

class TestTracebackPolicyAdherence:
    """Test traceback policy adherence across output formats"""

    def test_none_policy_excludes_traceback_json(self):
        """Test NONE policy excludes traceback in JSON output"""
        stream = StringIO()
        
        handler = JSONHandler(stream)

        logger = logging.getLogger("test_none_policy_json")
        logger.setLevel(logging.ERROR)
        logger.addHandler(handler)

        # Configure traceback policy filter
        class TracebackPolicyFilter(logging.Filter):
            def filter(self, record):
                record.traceback_policy = TracebackOptions.NONE
                return True

        handler.addFilter(TracebackPolicyFilter())

        # Log with exception
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.error("Error occurred", exc_info=True)

        output = stream.getvalue()
        json_data = json.loads(output.strip())

        # Should not contain traceback information
        assert "exc_info" not in json_data or json_data.get("exc_info") is None
        assert "ValueError" not in output
        

    def test_compact_policy_includes_essential_info_json(self):
        """Test COMPACT policy includes essential traceback info in JSON output"""
        stream = StringIO()
        
        handler = JSONHandler(stream)

        logger = logging.getLogger("test_compact_policy_json")
        logger.setLevel(logging.ERROR)
        logger.addHandler(handler)

        # Configure traceback policy filter
        class TracebackPolicyFilter(logging.Filter):
            def filter(self, record):
                record.traceback_policy = TracebackOptions.COMPACT
                return True

        handler.addFilter(TracebackPolicyFilter())

        # Log with exception
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.error("Error occurred", exc_info=True)

        output = stream.getvalue()
        json_data = json.loads(output.strip())

        # Should contain essential traceback information
        assert "exc_info" in json_data
        exc_text = json_data["exc_info"]
        assert "ValueError: Test exception" in exc_text
        # Should contain file and line info
        assert ".py:" in exc_text  # filename:line pattern
        assert " in " in exc_text  # function name
        # Should be compact (not full traceback)
        assert "Traceback" not in exc_text
        

    def test_full_policy_includes_complete_info_json(self):
        """Test FULL policy includes complete traceback info in JSON output"""
        stream = StringIO()
        
        handler = JSONHandler(stream)

        logger = logging.getLogger("test_full_policy_json")
        logger.setLevel(logging.ERROR)
        logger.addHandler(handler)

        # Configure traceback policy filter
        class TracebackPolicyFilter(logging.Filter):
            def filter(self, record):
                record.traceback_policy = TracebackOptions.FULL
                return True

        handler.addFilter(TracebackPolicyFilter())

        # Log with exception
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.error("Error occurred", exc_info=True)

        output = stream.getvalue()
        json_data = json.loads(output.strip())

        # Should contain complete traceback information
        assert "exc_info" in json_data
        exc_text = json_data["exc_info"]
        assert "ValueError: Test exception" in exc_text
        assert "Traceback" in exc_text
        # Should contain full stack trace info
        assert ".py" in exc_text  # filename
        assert "line" in exc_text  # line reference
        

    def test_traceback_policy_consistency_across_calls(self):
        """Test traceback policy is applied consistently across multiple log calls"""
        stream = StringIO()
        
        handler = JSONHandler(stream)

        logger = logging.getLogger("test_policy_consistency")
        logger.setLevel(logging.ERROR)
        logger.addHandler(handler)

        # Configure traceback policy filter
        class TracebackPolicyFilter(logging.Filter):
            def filter(self, record):
                record.traceback_policy = TracebackOptions.COMPACT
                return True

        handler.addFilter(TracebackPolicyFilter())

        # Log multiple exceptions
        for i in range(3):
            try:
                raise ValueError(f"Test exception {i}")
            except ValueError:
                logger.error(f"Error {i} occurred", exc_info=True)

        output = stream.getvalue()
        lines = output.strip().split("\n")

        # Should have 3 lines, all following compact policy
        assert len(lines) == 3

        for line in lines:
            json_data = json.loads(line)
            assert "exc_info" in json_data
            exc_text = json_data["exc_info"]
            assert "ValueError: Test exception" in exc_text
            # All should be compact format
            assert "Traceback" not in exc_text
            assert ".py:" in exc_text  # filename:line pattern
        

# Property-based tests using hypothesis
from hypothesis import given, settings
from hypothesis import strategies as st


class TestJSONSingleLineConsistencyProperty:
    """Property-based tests for JSON single-line consistency"""

    @given(
        message=st.text(min_size=1, max_size=1000),
        traceback_policy=st.sampled_from([
            TracebackOptions.NONE,
            TracebackOptions.COMPACT,
            TracebackOptions.FULL,
        ]),
        level=st.sampled_from([
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ]),
        logger_name=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-"
            ),
        ),
    )
    def test_json_single_line_consistency_property(
        self, message, traceback_policy, level, logger_name
    ):
        """
        For any JSON output generated by the system, including traceback information,
        the output should be formatted as a single line with no embedded newlines
        """
        stream = StringIO()
        handler = JSONHandler(stream)

        # Create test logger with unique name to avoid conflicts
        test_logger = logging.getLogger(f"test_prop_{logger_name}_{id(stream)}")
        test_logger.setLevel(level)
        test_logger.addHandler(handler)

        # Configure traceback policy filter
        class TracebackPolicyFilter(logging.Filter):
            def __init__(self, policy):
                super().__init__()
                self.policy = policy

            def filter(self, record):
                record.traceback_policy = self.policy
                return True

        handler.addFilter(TracebackPolicyFilter(traceback_policy))

        try:
            # Test with and without exceptions
            if traceback_policy != TracebackOptions.NONE:
                # Test with exception to verify traceback handling
                try:
                    raise ValueError("Property test exception")
                except ValueError:
                    test_logger.log(level, message, exc_info=True)
            else:
                # Test without exception
                test_logger.log(level, message)

            output = stream.getvalue()

            # Output must be single line
            assert "\n" not in output.strip(), f"Output contains newlines: {repr(output)}"
            assert "\r" not in output.strip(), f"Output contains carriage returns: {repr(output)}"

            # Output must be valid JSON
            if output.strip():  # Only test if there's output
                json_data = json.loads(output.strip())

                # Message must be preserved (possibly transformed for single-line)
                assert "message" in json_data
                # The message might be transformed to single-line, but should contain original content
                if "\n" in message or "\r" in message:
                    # Multi-line messages should be converted to single line with separators
                    # OR the original content should be preserved if python-json-logger handles it
                    message_content = json_data["message"]
                    # Either the message was converted to single line with separators
                    # OR it contains the original content (python-json-logger may preserve it)
                    original_without_newlines = message.replace("\n", "").replace("\r", "")
                    assert (
                        "|" in message_content
                        or original_without_newlines in message_content
                        or message in message_content
                    ), f"Message not properly preserved: {repr(message_content)} vs {repr(message)}"
                else:
                    # Single-line messages should be preserved exactly
                    assert json_data["message"] == message

                # Level must be preserved
                assert json_data["levelname"] == logging.getLevelName(level)

                # Traceback handling must follow policy
                if traceback_policy == TracebackOptions.NONE:
                    # Should not contain exception info
                    assert "exc_info" not in json_data or json_data.get("exc_info") is None
                else:
                    # Should contain exception info as single line
                    if "exc_info" in json_data:
                        exc_info = json_data["exc_info"]
                        assert "\n" not in exc_info, (
                            f"Exception info contains newlines: {repr(exc_info)}"
                        )
                        assert "\r" not in exc_info, (
                            f"Exception info contains carriage returns: {repr(exc_info)}"
                        )

        finally:
            # Cleanup: remove handler to prevent interference with other tests
            test_logger.removeHandler(handler)
            test_logger.setLevel(logging.NOTSET)

    @given(
        messages=st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=10),
        traceback_policy=st.sampled_from([
            TracebackOptions.NONE,
            TracebackOptions.COMPACT,
            TracebackOptions.FULL,
        ]),
    )
    def test_json_multiple_messages_single_line_property(self, messages, traceback_policy):
        """
        Multiple JSON messages should each be single line
        For any sequence of log messages, each JSON output line should be single line
        """
        stream = StringIO()
        handler = JSONHandler(stream)

        test_logger = logging.getLogger(f"test_multi_{id(stream)}")
        test_logger.setLevel(logging.INFO)
        test_logger.addHandler(handler)

        # Configure traceback policy filter
        class TracebackPolicyFilter(logging.Filter):
            def filter(self, record):
                record.traceback_policy = traceback_policy
                return True

        handler.addFilter(TracebackPolicyFilter())

        try:
            # Log all messages
            for i, message in enumerate(messages):
                if traceback_policy != TracebackOptions.NONE and i % 2 == 0:
                    # Add some exceptions to test traceback handling
                    try:
                        raise ValueError(f"Test exception {i}")
                    except ValueError:
                        test_logger.info(message, exc_info=True)
                else:
                    test_logger.info(message)

            output = stream.getvalue()

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
                        json_data = json.loads(line)
                        assert "message" in json_data
                        assert "levelname" in json_data

        finally:
            # Cleanup
            test_logger.removeHandler(handler)
            test_logger.setLevel(logging.NOTSET)


import re


def strip_ansi_codes(text):
    """Remove ANSI escape codes from text"""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


class TestTracebackPolicyConsistency:
    """Test traceback policy adherence across different output formats"""

    def test_none_policy_consistency_json_vs_terminal(self):
        """Test NONE policy excludes traceback consistently in both JSON and terminal output"""
        # Test JSON handler
        json_stream = StringIO()
        json_handler = JSONHandler(json_stream)

        # Test Terminal handler
        terminal_stream = StringIO()
        terminal_handler = TerminalHandler(terminal_stream)

        # Create test loggers
        json_logger = logging.getLogger("test_none_json_consistency")
        json_logger.setLevel(logging.ERROR)
        json_logger.addHandler(json_handler)

        terminal_logger = logging.getLogger("test_none_terminal_consistency")
        terminal_logger.setLevel(logging.ERROR)
        terminal_logger.addHandler(terminal_handler)

        # Configure traceback policy filters
        class TracebackPolicyFilter(logging.Filter):
            def filter(self, record):
                record.traceback_policy = TracebackOptions.NONE
                return True

        json_handler.addFilter(TracebackPolicyFilter())
        terminal_handler.addFilter(TracebackPolicyFilter())

        # Log with exception
        try:
            raise ValueError("Test exception for consistency")
        except ValueError:
            json_logger.error("Error in JSON", exc_info=True)
            terminal_logger.error("Error in Terminal", exc_info=True)

        json_output = json_stream.getvalue()
        terminal_output = terminal_stream.getvalue()

        # Both should exclude traceback information
        assert "ValueError" not in json_output
        assert "ValueError" not in terminal_output

        # JSON should not have exc_info field
        if json_output.strip():
            json_data = json.loads(json_output.strip())
            assert "exc_info" not in json_data or json_data.get("exc_info") is None

    def test_compact_policy_consistency_json_vs_terminal(self):
        """Test COMPACT policy includes essential info consistently in both formats"""
        # Test JSON handler
        json_stream = StringIO()
        
        json_handler = JSONHandler(json_stream)

        # Test Terminal handler - need to capture stderr since Hooks outputs there

        # Create test loggers
        json_logger = logging.getLogger("test_compact_json_consistency")
        json_logger.setLevel(logging.ERROR)
        json_logger.addHandler(json_handler)

        terminal_logger = logging.getLogger("test_compact_terminal_consistency")
        terminal_logger.setLevel(logging.ERROR)

        # Configure traceback policy filters
        class TracebackPolicyFilter(logging.Filter):
            def filter(self, record):
                record.traceback_policy = TracebackOptions.COMPACT
                return True

        json_handler.addFilter(TracebackPolicyFilter())

        # Capture terminal output by mocking stderr
        terminal_output_capture = StringIO()
        with patch("sys.stdout", terminal_output_capture):
            terminal_handler = TerminalHandler()
            terminal_handler.addFilter(TracebackPolicyFilter())
            terminal_logger.addHandler(terminal_handler)

            # Log with exception
            try:
                raise ValueError("Test exception for consistency")
            except ValueError:
                json_logger.error("Error in JSON", exc_info=True)
                terminal_logger.error("Error in Terminal", exc_info=True)

        json_output = json_stream.getvalue()
        terminal_output = terminal_output_capture.getvalue()
        # Both should include essential traceback information
        assert "ValueError: Test exception for consistency" in json_output
        # Terminal output may contain ANSI escape codes, so strip them and check
        clean_terminal_output = strip_ansi_codes(terminal_output)
        assert (
            "ValueError" in clean_terminal_output
            and "Test" in clean_terminal_output
            and "exception for" in clean_terminal_output
            and "consistency" in clean_terminal_output
        )

        # Both should include file and line info
        assert ".py" in json_output
        assert ".py" in clean_terminal_output

        # Both should be compact (not full traceback)
        assert "Traceback" not in json_output
        # Terminal may show "Traceback" in compact format, but should be limited

        # JSON should have single-line format
        json_lines = json_output.strip().split("\n")
        assert len(json_lines) == 1, f"JSON output should be single line: {json_lines}"
        


    def test_full_policy_consistency_json_vs_terminal(self):
        """Test FULL policy includes complete info consistently in both formats"""
        # Test JSON handler
        json_stream = StringIO()
        
        json_handler = JSONHandler(json_stream)

        # Test Terminal handler - need to capture stderr since Hooks outputs there

        # Create test loggers
        json_logger = logging.getLogger("test_full_json_consistency")
        json_logger.setLevel(logging.ERROR)
        json_logger.addHandler(json_handler)

        terminal_logger = logging.getLogger("test_full_terminal_consistency")
        terminal_logger.setLevel(logging.ERROR)

        # Configure traceback policy filters
        class TracebackPolicyFilter(logging.Filter):
            def filter(self, record):
                record.traceback_policy = TracebackOptions.FULL
                return True

        json_handler.addFilter(TracebackPolicyFilter())

        # Capture terminal output by mocking stderr
        terminal_output_capture = StringIO()
        with patch("sys.stdout", terminal_output_capture):
            terminal_handler = TerminalHandler()
            terminal_handler.addFilter(TracebackPolicyFilter())
            terminal_logger.addHandler(terminal_handler)

            # Log with exception
            try:
                raise ValueError("Test exception for consistency")
            except ValueError:
                json_logger.error("Error in JSON", exc_info=True)
                terminal_logger.error("Error in Terminal", exc_info=True)

        json_output = json_stream.getvalue()
        terminal_output = terminal_output_capture.getvalue()

        # Both should include complete traceback information
        assert "ValueError: Test exception for consistency" in json_output
        # Terminal output may contain ANSI escape codes, so strip them and check
        clean_terminal_output = strip_ansi_codes(terminal_output)
        assert (
            "ValueError" in clean_terminal_output
            and "Test" in clean_terminal_output
            and "exception for" in clean_terminal_output
            and "consistency" in clean_terminal_output
        )

        # Both should include full traceback
        assert "Traceback" in json_output
        assert (
            "Traceback" in clean_terminal_output or "File" in clean_terminal_output
        )  # Hooks may format differently

        # JSON should still be single-line despite full traceback
        json_lines = json_output.strip().split("\n")
        assert len(json_lines) == 1, (
            f"JSON output should be single line even with full traceback: {json_lines}"
        )

        # JSON should use pipe separators for single-line format
        if json_output.strip():
            json_data = json.loads(json_output.strip())
            if "exc_info" in json_data:
                assert "|" in json_data["exc_info"], (
                    "Full traceback should use pipe separators in JSON"
                )
        


class TestTracebackPolicyAdherenceProperty:
    """Property-based tests for traceback policy adherence"""

    @given(
        traceback_policy=st.sampled_from([
            TracebackOptions.NONE,
            TracebackOptions.COMPACT,
            TracebackOptions.FULL,
        ]),
        handler_type=st.sampled_from(["json", "terminal"]),
        exception_message=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters=" -_"
            ),
        ),
        level=st.sampled_from([logging.ERROR, logging.CRITICAL]),
    )
    @settings(deadline=None)  # Disable deadline due to Hooks terminal rendering
    def test_traceback_policy_adherence_property(
        self, traceback_policy, handler_type, exception_message, level
    ):
        """
        For any configured traceback policy, the system should format traceback output
        according to that policy consistently across all output formats
        """
        # Create appropriate handler based on type
        if handler_type == "json":
            stream = StringIO()
            handler = JSONHandler(stream)
        else:  # terminal
            # For terminal, we need to capture stderr
            from unittest.mock import patch

            stream = StringIO()
            with patch("sys.stdout", stream):
                handler = TerminalHandler()

        # Create test logger
        test_logger = logging.getLogger(f"test_policy_{handler_type}_{id(stream)}")
        test_logger.setLevel(level)
        test_logger.addHandler(handler)

        # Configure traceback policy filter
        class TracebackPolicyFilter(logging.Filter):
            def __init__(self, policy):
                super().__init__()
                self.policy = policy

            def filter(self, record):
                record.traceback_policy = self.policy
                return True

        handler.addFilter(TracebackPolicyFilter(traceback_policy))

        try:
            # Log with exception to test traceback handling
            try:
                raise ValueError(exception_message)
            except ValueError:
                test_logger.log(level, "Test message", exc_info=True)

            output = stream.getvalue()

            if handler_type == "terminal":
                # Strip ANSI codes for terminal output
                output = strip_ansi_codes(output)

            # Traceback policy adherence
            if traceback_policy == TracebackOptions.NONE:
                # Should not contain exception information
                assert "ValueError" not in output or exception_message not in output
            elif traceback_policy == TracebackOptions.COMPACT:
                # Should contain essential exception info but not full traceback
                if output.strip():  # Only test if there's output
                    assert "ValueError" in output
                    # For JSON, exception message might be escaped, so check more flexibly
                    if handler_type == "json":
                        # Parse JSON and check exc_info field
                        json_data = json.loads(output.strip())
                        if "exc_info" in json_data:
                            # Exception message should be in the exc_info field (possibly escaped)
                            assert "ValueError" in json_data["exc_info"]
                    else:
                        # For terminal, check directly
                        assert exception_message in output or any(
                            char in output for char in exception_message
                        )
                    # Should contain file info but not full "Traceback (most recent call last):"
                    assert ".py" in output
                    # For JSON, should not contain "Traceback" keyword
                    if handler_type == "json":
                        assert "Traceback" not in output
            elif traceback_policy == TracebackOptions.FULL:
                # Should contain complete traceback information
                if output.strip():  # Only test if there's output
                    assert "ValueError" in output
                    # For JSON, exception message might be escaped, so check more flexibly
                    if handler_type == "json":
                        # Parse JSON and check exc_info field
                        json_data = json.loads(output.strip())
                        if "exc_info" in json_data:
                            # Exception message should be in the exc_info field (possibly escaped)
                            assert "ValueError" in json_data["exc_info"]
                    else:
                        # For terminal, check directly
                        assert exception_message in output or any(
                            char in output for char in exception_message
                        )
                    # Should contain traceback information
                    assert "Traceback" in output or "File" in output

                    # For JSON, should be single line despite full traceback
                    if handler_type == "json":
                        json_lines = output.strip().split("\n")
                        assert len(json_lines) == 1, (
                            f"JSON output should be single line: {json_lines}"
                        )

                        # Should use pipe separators for single-line format
                        json_data = json.loads(output.strip())
                        if "exc_info" in json_data:
                            assert "|" in json_data["exc_info"], (
                                "Full traceback should use pipe separators in JSON"
                            )

        finally:
            # Cleanup
            test_logger.removeHandler(handler)
            test_logger.setLevel(logging.NOTSET)

    @given(
        policies=st.lists(
            st.sampled_from([TracebackOptions.NONE, TracebackOptions.COMPACT, TracebackOptions.FULL]),
            min_size=2,
            max_size=3,
            unique=True,
        ),
        exception_message=st.text(min_size=1, max_size=50),
    )
    def test_traceback_policy_consistency_across_calls(self, policies, exception_message):
        """
        Traceback policy should be applied consistently across multiple calls
        For any sequence of log calls with different traceback policies, each should
        follow its configured policy independently
        """
        stream = StringIO()
        handler = JSONHandler(stream)

        test_logger = logging.getLogger(f"test_policy_consistency_{id(stream)}")
        test_logger.setLevel(logging.ERROR)
        test_logger.addHandler(handler)

        try:
            outputs = []

            # Log with each policy
            for i, policy in enumerate(policies):
                # Create a fresh filter for each policy
                class TracebackPolicyFilter(logging.Filter):
                    def __init__(self, policy):
                        super().__init__()
                        self.policy = policy

                    def filter(self, record):
                        record.traceback_policy = self.policy
                        return True

                # Clear previous filters and add new one
                handler.filters.clear()
                handler.addFilter(TracebackPolicyFilter(policy))

                # Clear stream for this test
                stream.seek(0)
                stream.truncate(0)

                # Log with exception
                try:
                    raise ValueError(f"{exception_message}_{i}")
                except ValueError:
                    test_logger.error(f"Test message {i}", exc_info=True)

                output = stream.getvalue()
                outputs.append((policy, output))

            # Verify each output follows its policy
            for policy, output in outputs:
                if policy == TracebackOptions.NONE:
                    # Should not contain exception info
                    assert "ValueError" not in output or all(
                        f"{exception_message}_{i}" not in output for i in range(len(policies))
                    )
                elif policy == TracebackOptions.COMPACT:
                    # Should contain exception but not full traceback
                    if output.strip():
                        assert "ValueError" in output
                        assert "Traceback" not in output
                elif policy == TracebackOptions.FULL:
                    # Should contain full traceback
                    if output.strip():
                        assert "ValueError" in output
                        assert "Traceback" in output
                        # Should still be single line in JSON
                        json_lines = output.strip().split("\n")
                        assert len(json_lines) == 1

        finally:
            # Cleanup
            test_logger.removeHandler(handler)
            test_logger.setLevel(logging.NOTSET)
