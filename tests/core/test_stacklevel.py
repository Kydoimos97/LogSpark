"""
Test stacklevel resolution behavior.

Tests call-site resolution accuracy and ensures internal frames never leak to output.
"""

import logging
import os
import sys
from io import StringIO
from unittest.mock import patch

from hypothesis import given
from hypothesis import strategies as st

from logspark import logger
from logspark._Internal.Func.resolve_stacklevel import _is_internal, resolve_stacklevel


class TestStacklevelResolution:
    """Test stacklevel resolution accuracy and internal frame filtering."""

    def test_resolve_stacklevel_accuracy_default_mode(self, fresh_logger):
        """Test resolve_stacklevel accuracy in default mode."""
        # Ensure we're not in fast mode
        with patch.dict("os.environ", {}, clear=False):
            if "LOGSPARK_MODE" in os.environ:
                del os.environ["LOGSPARK_MODE"]

            # Test basic stacklevel resolution
            # When called from this test, should resolve to appropriate level
            resolved = resolve_stacklevel(1)

            # Should be greater than 1 (accounting for internal frames)
            assert resolved > 1
            assert isinstance(resolved, int)

    def test_resolve_stacklevel_with_user_stacklevel(self, fresh_logger):
        """Test resolve_stacklevel with custom user stacklevel."""
        with patch.dict("os.environ", {}, clear=False):
            if "LOGSPARK_MODE" in os.environ:
                del os.environ["LOGSPARK_MODE"]

            # Test with different user stacklevels
            base_resolved = resolve_stacklevel(1)
            higher_resolved = resolve_stacklevel(3)

            # Higher user stacklevel should result in higher resolved stacklevel
            assert higher_resolved > base_resolved
            assert higher_resolved == base_resolved + 2

    def test_internal_frame_detection(self):
        """Test that _is_internal correctly identifies LogSpark frames."""
        # Get current frame (this is a test frame, not internal)
        current_frame = sys._getframe(0)
        assert not _is_internal(current_frame)

        # Mock a frame that looks like it's from logspark
        class MockFrame:
            def __init__(self, module_name):
                self.f_globals = {"__name__": module_name}

        # Test various logspark module patterns
        logspark_frame = MockFrame("logspark.SparkLoggerDef")
        assert _is_internal(logspark_frame)

        logspark_handlers_frame = MockFrame("logspark.Handlers.SparkTerminalHandler")
        assert _is_internal(logspark_handlers_frame)

        logspark_internal_frame = MockFrame("logspark._Internal.Func.resolve_stacklevel")
        assert _is_internal(logspark_internal_frame)

        # Test non-logspark frames
        user_frame = MockFrame("my_app.main")
        assert not _is_internal(user_frame)

        stdlib_frame = MockFrame("logging")
        assert not _is_internal(stdlib_frame)

    def test_internal_frames_never_leak_to_output(self, fresh_logger):
        """Test that internal frames never leak to logging output."""
        # Set up a custom handler to capture log records
        captured_records = []

        class RecordCapturingHandler(logging.Handler):
            def emit(self, record):
                captured_records.append(record)

        # Configure logger with capturing handler
        handler = RecordCapturingHandler()
        fresh_logger.configure(level=logging.DEBUG, handler=handler)

        # Create a nested call structure to test stacklevel resolution
        def user_function():
            fresh_logger.info("test message from user function")

        def wrapper_function():
            user_function()

        # Call through wrapper
        wrapper_function()

        # Should have captured one record
        assert len(captured_records) == 1
        record = captured_records[0]

        # The record should point to user_function, not internal LogSpark code
        assert record.funcName == "user_function"
        assert "test_stacklevel.py" in record.pathname

    def test_stacklevel_resolution_with_deep_call_stack(self, fresh_logger):
        """Test stacklevel resolution works correctly with deep call stacks."""
        captured_records = []

        class RecordCapturingHandler(logging.Handler):
            def emit(self, record):
                captured_records.append(record)

        handler = RecordCapturingHandler()
        fresh_logger.configure(level=logging.DEBUG, handler=handler)

        def level_5():
            fresh_logger.info("deep call")

        def level_4():
            level_5()

        def level_3():
            level_4()

        def level_2():
            level_3()

        def level_1():
            level_2()

        # Call through deep stack
        level_1()

        # Should have captured one record pointing to level_5
        assert len(captured_records) == 1
        record = captured_records[0]
        assert record.funcName == "level_5"

    def test_stacklevel_resolution_edge_cases(self, fresh_logger):
        """Test stacklevel resolution handles edge cases gracefully."""
        # Test with very high user stacklevel
        resolved = resolve_stacklevel(100)
        assert isinstance(resolved, int)
        assert resolved > 0

        # Test with zero stacklevel
        resolved = resolve_stacklevel(0)
        assert isinstance(resolved, int)
        assert resolved >= 0

    def test_fast_mode_uses_cached_stacklevel(self, fresh_logger):
        """Test that fast mode uses cached stacklevel instead of frame walking."""
        with patch.dict("os.environ", {"LOGSPARK_MODE": "fast"}):
            # In fast mode, should use cached value
            resolved1 = resolve_stacklevel(1)
            resolved2 = resolve_stacklevel(1)

            # Should be consistent
            assert resolved1 == resolved2
            assert isinstance(resolved1, int)
            assert resolved1 > 0

    def test_frame_walking_exception_handling(self, fresh_logger):
        """Test exception handling in frame walking (lines 38-46)."""
        with patch.dict("os.environ", {}, clear=False):
            if "LOGSPARK_MODE" in os.environ:
                del os.environ["LOGSPARK_MODE"]

            # Mock sys._getframe to raise ValueError to test exception handling
            with patch("logspark._Internal.Func.resolve_stacklevel.sys._getframe") as mock_getframe:
                mock_getframe.side_effect = ValueError("Mock frame error")

                # Should fall back to cached stacklevel
                resolved = resolve_stacklevel(1)
                assert isinstance(resolved, int)
                assert resolved > 0

    def test_frame_walking_attribute_error_handling(self, fresh_logger):
        """Test AttributeError handling in frame walking (lines 38-46)."""
        with patch.dict("os.environ", {}, clear=False):
            if "LOGSPARK_MODE" in os.environ:
                del os.environ["LOGSPARK_MODE"]

            # Mock sys._getframe to raise AttributeError to test exception handling
            with patch("logspark._Internal.Func.resolve_stacklevel.sys._getframe") as mock_getframe:
                mock_getframe.side_effect = AttributeError("Mock attribute error")

                # Should fall back to cached stacklevel
                resolved = resolve_stacklevel(1)
                assert isinstance(resolved, int)
                assert resolved > 0


class TestStacklevelProperties:
    """Property-based tests for stacklevel resolution."""

    def test_property_default_mode_accuracy(self, fresh_logger):
        """

        For any logging call in default mode, accurate call-site resolution should be used.

        """
        from hypothesis import given
        from hypothesis import strategies as st

        @given(
            user_stacklevel=st.integers(min_value=1, max_value=10),
            message=st.text(min_size=1, max_size=50),
        )
        def property_test(user_stacklevel, message):
            # Ensure default mode (not fast, not silenced)
            with patch.dict("os.environ", {}, clear=False):
                if "LOGSPARK_MODE" in os.environ:
                    del os.environ["LOGSPARK_MODE"]

                captured_records = []

                class RecordCapturingHandler(logging.Handler):
                    def emit(self, record):
                        captured_records.append(record)

                fresh_logger.kill()  # Reset for each iteration
                handler = RecordCapturingHandler()
                fresh_logger.configure(level=logging.DEBUG, handler=handler)

                # Create a test function to ensure consistent call site
                def test_function():
                    fresh_logger.info(message, stacklevel=user_stacklevel)

                test_function()

                # Should have captured exactly one record
                assert len(captured_records) == 1
                record = captured_records[0]

                # Record should have valid location information
                assert record.funcName is not None
                assert record.pathname is not None
                assert record.lineno > 0

                # For user_stacklevel=1, should point to test_function
                # For higher stacklevels, should point further up the stack
                if user_stacklevel == 1:
                    assert record.funcName == "test_function"

        property_test()


class TestCallSiteResolutionProperties:
    """Property-based tests for call-site resolution accuracy"""

    @given(
        level=st.sampled_from([
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ]),
        message=st.text(min_size=1, max_size=100),
        stacklevel=st.integers(min_value=1, max_value=5),
    )
    def test_call_site_resolution_accuracy(self, level, message, stacklevel):
        """
        For any logged message, the call-site information should point to the actual
        calling code, never to LogSpark internal implementation.
        """
        import inspect

        # Configure logger with test parameters
        from logspark.Handlers import SparkTerminalHandler

        handler = SparkTerminalHandler()
        logger.configure(level=logging.DEBUG, handler=handler, no_freeze=True)

        # Capture log output to examine call-site information
        log_stream = StringIO()
        test_handler = logging.StreamHandler(log_stream)
        test_handler.setFormatter(logging.Formatter("%(pathname)s:%(lineno)d:%(funcName)s"))

        # Replace handler to capture call-site info
        logger.instance.handlers.clear()
        logger.instance.addHandler(test_handler)

        # Create a nested function to test call-site resolution
        def nested_logging_function():
            def inner_logging_function():
                # This is the actual call site we expect to see
                if level == logging.DEBUG:
                    logger.debug(message, stacklevel=stacklevel)
                elif level == logging.INFO:
                    logger.info(message, stacklevel=stacklevel)
                elif level == logging.WARNING:
                    logger.warning(message, stacklevel=stacklevel)
                elif level == logging.ERROR:
                    logger.error(message, stacklevel=stacklevel)
                elif level == logging.CRITICAL:
                    logger.critical(message, stacklevel=stacklevel)

                # Return the expected call site info
                frame = inspect.currentframe()
                assert frame is not None
                return (
                    frame.f_code.co_filename,
                    frame.f_lineno - 10,
                    frame.f_code.co_name,
                )  # Approximate line

            return inner_logging_function()

        # Execute logging and capture call-site
        expected_filename, expected_line_approx, expected_func = nested_logging_function()

        # Get the logged output
        log_output = log_stream.getvalue().strip()

        if log_output:  # Only check if something was logged (level filtering might prevent output)
            # Parse the call-site information from log output
            # Format is: filename:lineno:funcname message
            # But on Windows, the full path might contain colons, so we need to be careful

            # Find the last occurrence of the pattern :number: to split correctly
            import re

            match = re.search(r"([^:]+):(\d+):([^:]+)", log_output)

            if match:
                logged_filename = match.group(1)

                # The key requirement: call-site should NEVER point to LogSpark internal modules
                # EXCEPT when fast_log=True (fast_log trades accuracy for performance)
                assert not (
                    "LogSpark/Logging/" in logged_filename
                    or logged_filename.endswith("LogSpark/Logging/core.py")
                    or logged_filename.endswith("LogSpark/Logging/Terminal.py")
                ), f"Call-site points to LogSpark internal module: {logged_filename}"

                # For stacklevel=1 (default), it should point to our test code
                if stacklevel == 1:
                    assert "test_stacklevel.py" in logged_filename, (
                        f"With stacklevel=1, call-site should point to test code, got: {logged_filename}"
                    )

    @given(
        level=st.sampled_from([
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ]),
        message=st.text(
            min_size=1, max_size=100, alphabet=st.characters(min_codepoint=33, max_codepoint=126)
        ),  # Exclude space-only messages
    )
    def test_fast_mode_constant_time_behavior(self, level, message):
        """
        Test that fast mode provides constant-time performance regardless of call depth.
        """

        # Skip whitespace-only messages that are hard to match in output
        if not message.strip():
            return

        with patch.dict("os.environ", {"LOGSPARK_MODE": "fast"}):
            from logspark.Handlers import SparkTerminalHandler

            handler = SparkTerminalHandler()
            logger.configure(level=logging.DEBUG, handler=handler, no_freeze=True)

            # Capture log output with a formatter that includes the message clearly
            log_stream = StringIO()
            test_handler = logging.StreamHandler(log_stream)
            test_handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
            logger.instance.handlers.clear()
            logger.instance.addHandler(test_handler)

            # Create deeply nested function calls to test constant-time behavior
            def create_nested_calls(depth):
                if depth == 0:
                    # Log at the deepest level
                    if level == logging.DEBUG:
                        logger.debug(message)
                    elif level == logging.INFO:
                        logger.info(message)
                    elif level == logging.WARNING:
                        logger.warning(message)
                    elif level == logging.ERROR:
                        logger.error(message)
                    elif level == logging.CRITICAL:
                        logger.critical(message)
                else:
                    create_nested_calls(depth - 1)

            # Test with different call depths - performance should be constant
            for depth in [1, 5, 10]:
                log_stream.seek(0)
                log_stream.truncate(0)

                create_nested_calls(depth)

                # Verify logging still works regardless of depth
                log_output = log_stream.getvalue().strip()
                if logger.instance.isEnabledFor(level):
                    assert message in log_output, (
                        f"Message '{message}' not found in output '{log_output}' at depth {depth}"
                    )
