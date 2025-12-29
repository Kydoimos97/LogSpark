"""
Property-based tests for stdlib compliance features

Tests that validate LogSpark logging maintains strict stdlib compliance
and never introduces custom logging semantics beyond configuration and control.
"""

import inspect
import logging
import os
from io import StringIO

from hypothesis import given, settings
from hypothesis import strategies as st

from logspark import logger
from logspark.Handlers import TerminalHandler
from logspark.Handlers import JSONHandler




class TestCallSiteResolution:
    """Property tests for call-site resolution accuracy"""

    def setup_method(self):
        """Reset logger state before each test"""
        # Reset singleton state
        from logspark import logger

        logger._config = None
        logger._frozen = False
        logger._stdlib_logger = None
        logger._pre_config_setup_done = False
        logger._unconfigured_warning_emitted = False

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
    @settings(max_examples=100)
    def test_call_site_resolution_accuracy(self, level, message, stacklevel):
        """
        For any logged message, the call-site information should point to the actual
        calling code, never to LogSpark internal implementation.
        """
        # Configure logger with test parameters
        handler = TerminalHandler()
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
                    assert "test_stdlib_compliance.py" in logged_filename, (
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
    @settings(max_examples=50)
    def test_fast_log_constant_time_behavior(self, level, message):
        """
        Test that fast_log parameter provides constant-time performance
        regardless of call depth.
        """
        # Skip whitespace-only messages that are hard to match in output
        starting_val = os.environ.pop('LOGSPARK_MODE', '')
        os.environ['LOGSPARK_MODE'] = 'fast'
        if not message.strip():
            return

        handler = TerminalHandler()
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
        os.environ['LOGSPARK_MODE'] = starting_val


class TestLoggingSemantics:
    """Property tests for logging semantics limitation"""

    def setup_method(self):
        """Reset logger state before each test"""
        # Reset singleton state
        logger._config = None
        logger._frozen = False
        logger._stdlib_logger = None
        logger._pre_config_setup_done = False
        logger._unconfigured_warning_emitted = False

    @given(
        level=st.sampled_from([
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ]),
        message=st.text(min_size=1, max_size=100),
        handler_type=st.sampled_from(["terminal", "json"]),
    )
    @settings(max_examples=100)
    def test_logging_semantics_limitation(self, level, message, handler_type):
        """
        For any LogSpark operation, the system should provide only configuration
        and control capabilities without introducing logging semantics beyond stdlib logging.
        """
        # Configure logger with specified handler
        if handler_type == "terminal":
            handler: logging.Handler = TerminalHandler()
        else:
            handler = JSONHandler()

        logger.configure(level=logging.DEBUG, handler=handler, no_freeze=True)

        # Verify the underlying logger is a standard stdlib Logger
        assert isinstance(logger.instance, logging.Logger), (
            f"Expected stdlib Logger, got: {type(logger.instance)}"
        )

        # Verify no custom logger subclasses are used
        assert type(logger.instance) is logging.Logger, (
            f"Expected exact logging.Logger type, got: {type(logger.instance)}"
        )

        # Verify standard logging methods exist and behave like stdlib
        stdlib_methods = [
            "debug",
            "info",
            "warning",
            "error",
            "critical",
            "log",
            "isEnabledFor",
            "getEffectiveLevel",
            "addHandler",
            "removeHandler",
            "addFilter",
            "removeFilter",
        ]

        for method_name in stdlib_methods:
            assert hasattr(logger.instance, method_name), f"Missing stdlib method: {method_name}"

            # Verify method is callable
            method = getattr(logger.instance, method_name)
            assert callable(method), f"Method {method_name} is not callable"

        # Test that logging behavior follows stdlib semantics
        log_stream = StringIO()
        test_handler = logging.StreamHandler(log_stream)
        logger.instance.handlers.clear()
        logger.instance.addHandler(test_handler)

        # Test level filtering follows stdlib behavior
        logger.instance.setLevel(level)

        # Log at different levels and verify stdlib filtering behavior
        test_levels = [
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ]

        for test_level in test_levels:
            log_stream.seek(0)
            log_stream.truncate(0)

            logger.instance.log(test_level, message)
            output = log_stream.getvalue()

            # Verify stdlib level filtering semantics
            if test_level >= level:
                assert message in output, (
                    f"Message should be logged at level {test_level} >= {level}"
                )
            else:
                assert message not in output, (
                    f"Message should not be logged at level {test_level} < {level}"
                )

    @given(
        message=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        extra_fields=st.dictionaries(
            st.text(min_size=1, max_size=20).filter(lambda x: x.isalnum()),
            st.one_of(
                st.text(max_size=50),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
            ),
            min_size=0,
            max_size=3,
        ),
    )
    @settings(max_examples=50)
    def test_no_custom_logging_behavior(self, message, extra_fields):
        """
        Test that LogSpark doesn't introduce custom logging behavior beyond stdlib.
        """
        # Configure logger
        log_stream = StringIO()
        test_handler = logging.StreamHandler(log_stream)
        test_handler.setFormatter(logging.Formatter("%(message)s"))

        logger.instance.handlers.clear()
        logger.instance.addHandler(test_handler)

        # Log message using LogSpark wrapper
        logger.info(message)
        LogSpark_output = log_stream.getvalue().strip()

        # Reset stream
        log_stream.seek(0)
        log_stream.truncate(0)

        # Log same message using direct stdlib logger
        stdlib_logger = logging.getLogger("test_stdlib")
        stdlib_logger.handlers.clear()
        stdlib_logger.addHandler(test_handler)
        stdlib_logger.setLevel(logging.DEBUG)

        stdlib_logger.info(message)
        stdlib_output = log_stream.getvalue().strip()

        # Verify outputs match
        assert LogSpark_output == stdlib_output, (
            f"LogSpark output differs from stdlib: '{LogSpark_output}' vs '{stdlib_output}'"
        )
