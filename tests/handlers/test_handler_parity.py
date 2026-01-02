"""
Test handler parity and cross-handler consistency.
"""

import io
import json
import logging
import os
import sys
from unittest.mock import patch

import pytest

from logspark.Handlers.Terminal import TerminalHandler
from logspark.Types import TracebackOptions


def normalize_terminal_output(output: str) -> dict:
    """Normalize terminal output to extract semantic content"""
    # Extract key information from terminal output
    lines = output.strip().split("\n")
    if not lines or not lines[0].strip():
        return {}

    # Parse the main log line (simplified parsing)
    main_line = lines[0]

    result = {
        "has_timestamp": "[" in main_line and "]" in main_line,
        "has_level": any(
            level in main_line for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        ),
        "has_location": ".py:" in main_line,
        "message_present": True,  # Assume message is present if we have output
        "exception_info": len(lines) > 1,  # Exception info creates additional lines
        "raw_output": output,
    }

    return result


def normalize_json_output(output: str) -> dict:
    """Normalize JSON output to extract semantic content"""
    if not output.strip():
        return {}

    try:
        parsed = json.loads(output.strip())

        result = {
            "has_timestamp": "asctime" in parsed,
            "has_level": "levelname" in parsed,
            "has_location": "filename" in parsed and "lineno" in parsed,
            "message_present": "message" in parsed and bool(parsed.get("message", "").strip()),
            "exception_info": "exc_text" in parsed and parsed.get("exc_text") is not None,
            "structured_data": parsed,
        }

        return result
    except json.JSONDecodeError:
        return {"parse_error": True, "raw_output": output}


class TestHandlerSemanticEquivalence:
    """Test semantic equivalence across handlers for identical inputs"""

    def test_basic_message_consistency(self):
        """Test that all handlers produce semantically equivalent output for basic messages"""
        message = "Test log message"
        level = logging.INFO

        # Terminal handler output
        terminal_stream = io.StringIO()
        from logspark.Handlers.Terminal import TerminalHandler

        terminal_handler = TerminalHandler(
            stream=terminal_stream, no_rich=True
        )  # Force stdlib for consistency

        # JSON handler output (if available)
        try:
            from logspark.Handlers.Json import JSONHandler

            json_stream = io.StringIO()
            json_handler = JSONHandler(stream=json_stream)
            json_available = True
        except ImportError:
            json_available = False

        # PreConfig handler output
        preconfig_stream = io.StringIO()
        from logspark.Handlers.PreConfig import pre_config_handler

        preconfig_handler = pre_config_handler()
        # Replace stderr with our test stream
        preconfig_handler.stream = preconfig_stream

        # Create identical log records
        record_terminal = logging.LogRecord(
            name="test",
            level=level,
            pathname="test.py",
            lineno=42,
            msg=message,
            args=(),
            exc_info=None,
        )
        record_terminal.funcName = "test_function"

        record_json = logging.LogRecord(
            name="test",
            level=level,
            pathname="test.py",
            lineno=42,
            msg=message,
            args=(),
            exc_info=None,
        )
        record_json.funcName = "test_function"

        record_preconfig = logging.LogRecord(
            name="test",
            level=level,
            pathname="test.py",
            lineno=42,
            msg=message,
            args=(),
            exc_info=None,
        )
        record_preconfig.funcName = "test_function"

        # Emit to all handlers
        terminal_handler.emit(record_terminal)
        if json_available:
            json_handler.emit(record_json)
        preconfig_handler.emit(record_preconfig)

        # Normalize outputs
        terminal_output = normalize_terminal_output(terminal_stream.getvalue())
        preconfig_output = normalize_terminal_output(preconfig_stream.getvalue())

        # Verify semantic equivalence
        assert terminal_output["has_level"] == preconfig_output["has_level"]
        assert terminal_output["has_location"] == preconfig_output["has_location"]
        assert terminal_output["message_present"] == preconfig_output["message_present"]

        if json_available:
            json_output = normalize_json_output(json_stream.getvalue())
            assert json_output["has_level"]
            assert json_output["has_location"]
            assert json_output["message_present"]

    def test_exception_handling_consistency(self):
        """Test that handlers handle exceptions consistently"""
        message = "Error occurred"

        # Create handlers
        terminal_stream = io.StringIO()
        from logspark.Handlers.Terminal import TerminalHandler

        terminal_handler = TerminalHandler(stream=terminal_stream, no_rich=True)

        preconfig_stream = io.StringIO()
        from logspark.Handlers.PreConfig import pre_config_handler

        preconfig_handler = pre_config_handler()
        preconfig_handler.stream = preconfig_stream

        # Test with exception
        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()

        # Create records with exception
        record_terminal = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg=message,
            args=(),
            exc_info=exc_info,
        )

        record_preconfig = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg=message,
            args=(),
            exc_info=exc_info,
        )

        # Emit records
        terminal_handler.emit(record_terminal)
        preconfig_handler.emit(record_preconfig)

        # Both should produce output
        terminal_output = terminal_stream.getvalue()
        preconfig_output = preconfig_stream.getvalue()

        assert len(terminal_output) > 0
        assert len(preconfig_output) > 0
        assert message in terminal_output
        assert message in preconfig_output


class TestHandlerTracebackPolicyConsistency:
    """Test cross-handler consistency with same traceback policies"""

    def test_traceback_policy_none_consistency(self):
        """Test that NONE policy is applied consistently across handlers"""
        message = "Error with no traceback"

        # Create handlers
        terminal_stream = io.StringIO()
        from logspark.Handlers.Terminal import TerminalHandler

        terminal_handler = TerminalHandler(stream=terminal_stream, no_rich=True)

        json_available = True
        try:
            from logspark.Handlers.Json import JSONHandler

            json_stream = io.StringIO()
            json_handler = JSONHandler(stream=json_stream)
        except ImportError:
            json_available = False

        # Create exception
        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()

        # Create records with NONE policy
        record_terminal = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg=message,
            args=(),
            exc_info=exc_info,
        )
        record_terminal.traceback_policy = TracebackOptions.NONE

        if json_available:
            record_json = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg=message,
                args=(),
                exc_info=exc_info,
            )
            record_json.traceback_policy = TracebackOptions.NONE

        # Emit records
        terminal_handler.emit(record_terminal)
        if json_available:
            json_handler.emit(record_json)

        # Verify NONE policy was applied
        assert record_terminal.exc_info is None
        assert record_terminal.exc_text is None

        if json_available:
            assert record_json.exc_info is None
            assert record_json.exc_text is None

    def test_traceback_policy_compact_consistency(self):
        """Test that COMPACT policy produces consistent results across handlers"""
        message = "Error with compact traceback"

        # Create handlers
        terminal_stream = io.StringIO()
        from logspark.Handlers.Terminal import TerminalHandler

        terminal_handler = TerminalHandler(stream=terminal_stream, no_rich=True)

        json_available = True
        try:
            from logspark.Handlers.Json import JSONHandler

            json_stream = io.StringIO()
            json_handler = JSONHandler(stream=json_stream)
        except ImportError:
            json_available = False

        # Create exception
        try:
            raise ValueError("Test exception for compact")
        except ValueError:
            exc_info = sys.exc_info()

        # Create records with COMPACT policy
        record_terminal = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg=message,
            args=(),
            exc_info=exc_info,
        )
        record_terminal.traceback_policy = TracebackOptions.COMPACT

        if json_available:
            record_json = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg=message,
                args=(),
                exc_info=exc_info,
            )
            record_json.traceback_policy = TracebackOptions.COMPACT

        # Emit records
        terminal_handler.emit(record_terminal)
        if json_available:
            json_handler.emit(record_json)

        # Verify COMPACT policy was applied consistently
        assert record_terminal.exc_info is None  # Should be cleared
        assert record_terminal.exc_text is not None  # Should have compact format
        assert "ValueError: Test exception for compact" in record_terminal.exc_text

        if json_available:
            assert record_json.exc_info is None  # Should be cleared
            assert record_json.exc_text is not None  # Should have compact format
            assert "ValueError: Test exception for compact" in record_json.exc_text

    def test_traceback_policy_full_consistency(self):
        """Test that FULL policy is handled consistently across handlers"""
        message = "Error with full traceback"

        # Create handlers
        terminal_stream = io.StringIO()
        from logspark.Handlers.Terminal import TerminalHandler

        terminal_handler = TerminalHandler(stream=terminal_stream, no_rich=True)

        json_available = True
        try:
            from logspark.Handlers.Json import JSONHandler

            json_stream = io.StringIO()
            json_handler = JSONHandler(stream=json_stream)
        except ImportError:
            json_available = False

        # Create exception
        try:
            raise ValueError("Test exception for full")
        except ValueError:
            exc_info = sys.exc_info()

        # Create records with FULL policy
        record_terminal = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg=message,
            args=(),
            exc_info=exc_info,
        )
        record_terminal.traceback_policy = TracebackOptions.FULL

        if json_available:
            record_json = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg=message,
                args=(),
                exc_info=exc_info,
            )
            record_json.traceback_policy = TracebackOptions.FULL

        # Emit records
        terminal_handler.emit(record_terminal)
        if json_available:
            json_handler.emit(record_json)

        # For FULL policy, behavior may vary between handlers
        # Terminal handler lets Rich handle it, JSON handler formats it
        # But both should process without error

        # Verify outputs were produced
        terminal_output = terminal_stream.getvalue()
        assert len(terminal_output) > 0
        assert message in terminal_output

        if json_available:
            json_output = json_stream.getvalue()
            assert len(json_output) > 0

            # JSON should have structured exception info
            parsed = json.loads(json_output.strip())
            assert message in parsed["message"]


class TestHandlerEnvironmentConsistency:
    """Test that handlers behave consistently across environment modes"""

    def test_silenced_mode_consistency(self):
        """Test that all handlers respect silenced mode"""

        with patch.dict("os.environ", {"LOGSPARK_MODE": "silenced"}):
            # Terminal handler
            terminal_handler = TerminalHandler()
            # Should not use stdout in silenced mode
            if hasattr(terminal_handler._handler, "stream"):
                assert terminal_handler._handler.stream is not sys.stdout
            elif hasattr(terminal_handler._handler, "console"):
                assert terminal_handler._handler.console.file is not sys.stdout

            # JSON handler
            try:
                from logspark.Handlers.Json import JSONHandler

                json_handler = JSONHandler()
                # Should not use stdout in silenced mode
                assert json_handler.stream is not sys.stdout
            except ImportError:
                pass  # Skip if not available

            # PreConfig handler
            from logspark.Handlers.PreConfig import pre_config_handler

            preconfig_handler = pre_config_handler()
            # Should not use stderr in silenced mode
            assert preconfig_handler.stream is not sys.stderr

    def test_normal_mode_consistency(self):
        """Test that handlers use appropriate streams in normal mode"""
        with patch.dict("os.environ", {}, clear=False):
            if "LOGSPARK_MODE" in os.environ:
                del os.environ["LOGSPARK_MODE"]

            # Terminal handler should default to stdout
            terminal_handler = TerminalHandler()
            if hasattr(terminal_handler._handler, "stream"):
                assert terminal_handler._handler.stream is sys.stdout
            elif hasattr(terminal_handler._handler, "console"):
                assert terminal_handler._handler.console.file is sys.stdout

            # JSON handler should default to stdout
            try:
                from logspark.Handlers.Json import JSONHandler

                json_handler = JSONHandler()
                assert json_handler.stream is sys.stdout
            except ImportError:
                pass  # Skip if not available

            # PreConfig handler should use stderr
            from logspark.Handlers.PreConfig import pre_config_handler

            preconfig_handler = pre_config_handler()
            assert preconfig_handler.stream is sys.stderr


# Property-Based Tests
from hypothesis import given
from hypothesis import strategies as st


class TestHandlerParityProperties:
    """Property-based tests for handler parity and consistency"""

    @given(
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
        logger_name=st.text(
            min_size=1,
            max_size=100,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="._-"
            ),
        ),
        lineno=st.integers(min_value=1, max_value=10000),
        exception_message=st.text(
            min_size=1, max_size=200, alphabet=st.characters(min_codepoint=32, max_codepoint=126)
        ),
    )
    def test_property_traceback_policy_compact_consistency(
        self, message, level, logger_name, lineno, exception_message
    ):
        """

        For any log message and exception, COMPACT policy should be applied consistently across all handlers

        """
        # Create exception
        try:
            raise ValueError(exception_message)
        except ValueError:
            exc_info = sys.exc_info()

        # Test Terminal handler
        terminal_stream = io.StringIO()
        from logspark.Handlers.Terminal import TerminalHandler

        terminal_handler = TerminalHandler(stream=terminal_stream, no_rich=True)

        record_terminal = logging.LogRecord(
            name=logger_name,
            level=level,
            pathname="test.py",
            lineno=lineno,
            msg=message,
            args=(),
            exc_info=exc_info,
        )
        record_terminal.traceback_policy = TracebackOptions.COMPACT

        terminal_handler.emit(record_terminal)

        # Verify COMPACT policy was applied to terminal handler
        assert record_terminal.exc_info is None, (
            "Terminal handler should clear exc_info for COMPACT policy"
        )
        assert record_terminal.exc_text is not None, (
            "Terminal handler should set exc_text for COMPACT policy"
        )
        assert "ValueError" in record_terminal.exc_text, (
            "Terminal handler should include exception type"
        )

        # For property testing, we need to be more lenient about the exact format
        # The key requirement is that exception information is present and compact
        if exception_message.strip() and len(exception_message.strip()) > 0:
            # Only check for message inclusion if it's a reasonable string
            clean_message = exception_message.strip()
            if (
                len(clean_message) > 0
                and "\r" not in clean_message
                and "\n" not in clean_message
                and "\x00" not in clean_message
                and all(ord(c) >= 32 or c in "\t" for c in clean_message)
            ):
                assert clean_message in record_terminal.exc_text, (
                    "Terminal handler should include exception message"
                )

        # Test JSON handler (if available)
        try:
            from logspark.Handlers.Json import JSONHandler

            json_stream = io.StringIO()
            json_handler = JSONHandler(stream=json_stream)

            # Create fresh exception info for JSON handler
            try:
                raise ValueError(exception_message)
            except ValueError:
                exc_info_json = sys.exc_info()

            record_json = logging.LogRecord(
                name=logger_name,
                level=level,
                pathname="test.py",
                lineno=lineno,
                msg=message,
                args=(),
                exc_info=exc_info_json,
            )
            record_json.traceback_policy = TracebackOptions.COMPACT

            json_handler.emit(record_json)

            # Verify COMPACT policy was applied to JSON handler
            assert record_json.exc_info is None, (
                "JSON handler should clear exc_info for COMPACT policy"
            )

            # JSON handler might use different field names, check the output
            json_output = json_stream.getvalue()
            if json_output.strip():
                parsed = json.loads(json_output.strip())
                has_exception_info = ("exc_text" in parsed and parsed["exc_text"] is not None) or (
                    "exc_info" in parsed and parsed["exc_info"] is not None
                )
                assert has_exception_info, "JSON handler should have exception information"

                exc_field = parsed.get("exc_text") or parsed.get("exc_info")
                if exc_field:
                    assert "ValueError" in exc_field, "JSON handler should include exception type"
                    if exception_message.strip() and len(exception_message.strip()) > 0:
                        clean_message = exception_message.strip()
                        if (
                            len(clean_message) > 0
                            and "\r" not in clean_message
                            and "\n" not in clean_message
                            and "\x00" not in clean_message
                            and all(ord(c) >= 32 or c in "\t" for c in clean_message)
                        ):
                            assert clean_message in exc_field, (
                                "JSON handler should include exception message"
                            )
                    assert "\n" not in exc_field, "JSON handler exc_text should be single line"

            # Terminal handler should have compact format (may contain newlines in traceback part)
            # The key requirement is that it's more compact than a full traceback

        except ImportError:
            # JSON handler not available, skip JSON-specific tests
            pass

    @given(
        message=st.text(
            min_size=1, max_size=500, alphabet=st.characters(min_codepoint=32, max_codepoint=126)
        ),
        level=st.sampled_from([
            logging.ERROR,
            logging.CRITICAL,
        ]),  # Use error levels for exception testing
        logger_name=st.text(
            min_size=1,
            max_size=100,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="._-"
            ),
        ),
        lineno=st.integers(min_value=1, max_value=10000),
        exception_message=st.text(
            min_size=1, max_size=200, alphabet=st.characters(min_codepoint=32, max_codepoint=126)
        ),
    )
    def test_property_traceback_policy_full_consistency(
        self, message, level, logger_name, lineno, exception_message
    ):
        """

        For any log message and exception, FULL policy should be handled consistently across all handlers

        """
        # Create exception
        try:
            raise ValueError(exception_message)
        except ValueError:
            exc_info = sys.exc_info()

        # Test Terminal handler
        terminal_stream = io.StringIO()
        from logspark.Handlers.Terminal import TerminalHandler

        terminal_handler = TerminalHandler(stream=terminal_stream, no_rich=True)

        record_terminal = logging.LogRecord(
            name=logger_name,
            level=level,
            pathname="test.py",
            lineno=lineno,
            msg=message,
            args=(),
            exc_info=exc_info,
        )
        record_terminal.traceback_policy = TracebackOptions.FULL

        # Emit should not raise exception
        try:
            terminal_handler.emit(record_terminal)
        except Exception as e:
            pytest.fail(f"Terminal handler failed to emit FULL traceback record: {e}")

        # Verify output was produced
        terminal_output = terminal_stream.getvalue()
        assert len(terminal_output) > 0, "Terminal handler should produce output for FULL policy"
        assert message in terminal_output, "Terminal output should contain the message"

        # Test JSON handler (if available)
        try:
            from logspark.Handlers.Json import JSONHandler

            json_stream = io.StringIO()
            json_handler = JSONHandler(stream=json_stream)

            # Create fresh exception info for JSON handler
            try:
                raise ValueError(exception_message)
            except ValueError:
                exc_info_json = sys.exc_info()

            record_json = logging.LogRecord(
                name=logger_name,
                level=level,
                pathname="test.py",
                lineno=lineno,
                msg=message,
                args=(),
                exc_info=exc_info_json,
            )
            record_json.traceback_policy = TracebackOptions.FULL

            # Emit should not raise exception
            try:
                json_handler.emit(record_json)
            except Exception as e:
                pytest.fail(f"JSON handler failed to emit FULL traceback record: {e}")

            # Verify JSON output
            json_output = json_stream.getvalue()
            assert len(json_output) > 0, "JSON handler should produce output for FULL policy"

            # JSON output should be single line
            assert "\n" not in json_output.strip(), "JSON output should be single line"

            # Should be valid JSON
            parsed = json.loads(json_output.strip())
            assert message in parsed["message"], "JSON output should contain the message"

            # Should have exception information
            if "exc_text" in parsed and parsed["exc_text"]:
                exc_text = parsed["exc_text"]
                assert "ValueError" in exc_text, "JSON exc_text should include exception type"
                if exception_message.strip():
                    assert exception_message in exc_text, (
                        "JSON exc_text should include exception message"
                    )
                assert "\n" not in exc_text, "JSON exc_text should be single line"

        except ImportError:
            # JSON handler not available, skip JSON-specific tests
            pass

    @given(
        message=st.text(min_size=1, max_size=300),
        level=st.sampled_from([logging.INFO, logging.WARNING, logging.ERROR]),
        silenced=st.booleans(),
    )
    def test_property_handler_environment_consistency(self, message, level, silenced):
        """

        For any message and environment mode, all handlers should respect the environment consistently

        """
        env_patch = {"LOGSPARK_MODE": "silenced"} if silenced else {}

        with patch.dict("os.environ", env_patch, clear=False):
            if not silenced and "LOGSPARK_MODE" in os.environ:
                del os.environ["LOGSPARK_MODE"]

            # Test Terminal handler
            terminal_handler = TerminalHandler()

            if silenced:
                # In silenced mode, should not use stdout
                if hasattr(terminal_handler._handler, "stream"):
                    assert terminal_handler._handler.stream is not sys.stdout
                elif hasattr(terminal_handler._handler, "console"):
                    assert terminal_handler._handler.console.file is not sys.stdout
            else:
                # In normal mode, should use stdout by default
                if hasattr(terminal_handler._handler, "stream"):
                    assert terminal_handler._handler.stream is sys.stdout
                elif hasattr(terminal_handler._handler, "console"):
                    assert terminal_handler._handler.console.file is sys.stdout

            # Test JSON handler (if available)
            try:
                from logspark.Handlers.Json import JSONHandler

                json_handler = JSONHandler()

                if silenced:
                    assert json_handler.stream is not sys.stdout, (
                        "JSON handler should not use stdout in silenced mode"
                    )
                else:
                    assert json_handler.stream is sys.stdout, (
                        "JSON handler should use stdout in normal mode"
                    )
            except ImportError:
                pass  # Skip if not available

            # Test PreConfig handler
            from logspark.Handlers.PreConfig import pre_config_handler

            preconfig_handler = pre_config_handler()

            if silenced:
                assert preconfig_handler.stream is not sys.stderr, (
                    "PreConfig handler should not use stderr in silenced mode"
                )
            else:
                assert preconfig_handler.stream is sys.stderr, (
                    "PreConfig handler should use stderr in normal mode"
                )

            # All handlers should be able to emit messages without error
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="test.py",
                lineno=1,
                msg=message,
                args=(),
                exc_info=None,
            )

            try:
                terminal_handler.emit(record.copy() if hasattr(record, "copy") else record)
                preconfig_handler.emit(record.copy() if hasattr(record, "copy") else record)

                if "json_handler" in locals():
                    json_handler.emit(record.copy() if hasattr(record, "copy") else record)
            except Exception as e:
                pytest.fail(
                    f"Handler failed to emit in {'silenced' if silenced else 'normal'} mode: {e}"
                )

    @given(
        messages=st.lists(st.text(min_size=1, max_size=200), min_size=1, max_size=5),
        level=st.sampled_from([logging.INFO, logging.WARNING, logging.ERROR]),
    )
    def test_property_handler_output_consistency(self, messages, level):
        """

        For any sequence of messages, all handlers should produce consistent semantic output

        """
        # Create handlers with test streams
        terminal_stream = io.StringIO()
        from logspark.Handlers.Terminal import TerminalHandler

        terminal_handler = TerminalHandler(stream=terminal_stream, no_rich=True)

        preconfig_stream = io.StringIO()
        from logspark.Handlers.PreConfig import pre_config_handler

        preconfig_handler = pre_config_handler()
        preconfig_handler.stream = preconfig_stream

        json_available = True
        try:
            from logspark.Handlers.Json import JSONHandler

            json_stream = io.StringIO()
            json_handler = JSONHandler(stream=json_stream)
        except ImportError:
            json_available = False

        # Emit all messages to all handlers
        for i, message in enumerate(messages):
            record_terminal = logging.LogRecord(
                name="test",
                level=level,
                pathname="test.py",
                lineno=i + 1,
                msg=message,
                args=(),
                exc_info=None,
            )

            record_preconfig = logging.LogRecord(
                name="test",
                level=level,
                pathname="test.py",
                lineno=i + 1,
                msg=message,
                args=(),
                exc_info=None,
            )

            terminal_handler.emit(record_terminal)
            preconfig_handler.emit(record_preconfig)

            if json_available:
                record_json = logging.LogRecord(
                    name="test",
                    level=level,
                    pathname="test.py",
                    lineno=i + 1,
                    msg=message,
                    args=(),
                    exc_info=None,
                )
                json_handler.emit(record_json)

        # Verify all handlers produced output
        terminal_output = terminal_stream.getvalue()
        preconfig_output = preconfig_stream.getvalue()

        assert len(terminal_output) > 0, "Terminal handler should produce output"
        assert len(preconfig_output) > 0, "PreConfig handler should produce output"

        # Verify all messages appear in outputs
        for message in messages:
            if message.strip():  # Skip empty messages
                assert message in terminal_output, f"Terminal output should contain '{message}'"
                assert message in preconfig_output, f"PreConfig output should contain '{message}'"

        if json_available:
            json_output = json_stream.getvalue()
            assert len(json_output) > 0, "JSON handler should produce output"

            # JSON output should be valid and contain messages
            json_lines = [line.strip() for line in json_output.strip().split("\n") if line.strip()]
            assert len(json_lines) == len(messages), "JSON should produce one line per message"

            for line in json_lines:
                parsed = json.loads(line)
                assert "message" in parsed, "Each JSON line should have a message field"
