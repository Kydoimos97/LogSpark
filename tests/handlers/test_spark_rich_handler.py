"""
Test SparkRichHandler component for Rich-based logging.

Tests validate:
- Proper inheritance from RichHandler
- CustomLogRender integration
- Path resolution and formatting
- Log record rendering with all features
- Console and stream handling
- Function name and line number processing
"""

import io
import logging
import os
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

# Skip entire module if Rich is not available
pytest.importorskip("rich")

from rich.console import Console
from rich.text import Text
from rich.traceback import Traceback

from logspark.Hooks.SparkRichHandler import SparkRichHandler


class TestSparkRichHandlerInitialization:
    """Test SparkRichHandler initialization and configuration"""

    def test_default_initialization(self):
        """Test SparkRichHandler with default parameters"""
        handler = SparkRichHandler()

        # Should inherit from RichHandler
        from rich.logging import RichHandler

        assert isinstance(handler, RichHandler)

        # Should have CustomLogRender instance
        assert hasattr(handler, "_c_log_render")
        from logspark.Hooks.CustomLogRender import CustomLogRender

        assert isinstance(handler._c_log_render, CustomLogRender)

        # Check default configuration
        assert handler._c_log_render.show_time is True
        assert handler._c_log_render.show_level is True
        assert handler._c_log_render.show_path is True
        assert handler._c_log_render.show_function is False
        assert handler._c_log_render.omit_repeated_times is True
        assert handler._c_log_render.level_width == 8

    def test_custom_initialization(self):
        """Test SparkRichHandler with custom parameters"""
        console = Console(file=io.StringIO())

        handler = SparkRichHandler(
            level=logging.WARNING,
            console=console,
            show_time=False,
            show_level=False,
            show_path=False,
            show_function=True,
            markup=True,
            rich_tracebacks=True,
            log_time_format="%H:%M:%S",
        )

        # Check level setting
        assert handler.level == logging.WARNING

        # Check console setting
        assert handler.console is console

        # Check CustomLogRender configuration
        assert handler._c_log_render.show_time is False
        assert handler._c_log_render.show_level is False
        assert handler._c_log_render.show_path is False
        assert handler._c_log_render.show_function is True
        assert handler._c_log_render.time_format == "%H:%M:%S"

    def test_initialization_with_all_parameters(self):
        """Test SparkRichHandler with all possible parameters"""
        from rich.highlighter import NullHighlighter

        console = Console(file=io.StringIO())
        highlighter = NullHighlighter()

        handler = SparkRichHandler(
            level=logging.DEBUG,
            console=console,
            show_time=True,
            show_level=True,
            show_path=True,
            show_function=True,
            markup=False,
            rich_tracebacks=False,
            tracebacks_width=120,
            tracebacks_extra_lines=5,
            tracebacks_theme="monokai",
            tracebacks_word_wrap=False,
            tracebacks_show_locals=True,
            log_time_format="[%H:%M:%S]",
            highlighter=highlighter,
        )

        assert handler.level == logging.DEBUG
        assert handler.console is console
        assert handler._c_log_render.show_function is True
        assert handler._c_log_render.time_format == "[%H:%M:%S]"


class TestSparkRichHandlerPathResolution:
    """Test path resolution functionality"""

    def test_path_resolution_with_pythonpath(self):
        """Test path resolution when PYTHONPATH is set"""
        test_pythonpath = "/test/python/path"
        test_record_path = "/test/python/path/myproject/module.py"

        with patch.dict(os.environ, {"PYTHONPATH": test_pythonpath}):
            # Reload the module to pick up the new PYTHONPATH
            import importlib

            from logspark.Hooks import SparkRichHandler as shr_module

            importlib.reload(shr_module)

            handler = shr_module.SparkRichHandler()
            Console(file=io.StringIO())

            # Create a mock record
            record = Mock()
            record.pathname = test_record_path
            record.funcName = "test_function"
            record.lineno = 42
            record.created = datetime.now().timestamp()

            # Mock get_level_text method
            handler.get_level_text = Mock(return_value="INFO")
            handler.enable_link_path = False

            # Create mock message renderable
            message_renderable = Text("Test message")

            # Call render method
            result = handler.render(
                record=record, traceback=None, message_renderable=message_renderable
            )

            # Should return a renderable (Table from CustomLogRender)
            assert result is not None

    def test_path_resolution_without_pythonpath(self):
        """Test path resolution when PYTHONPATH is not set"""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure PYTHONPATH is not set
            if "PYTHONPATH" in os.environ:
                del os.environ["PYTHONPATH"]

            # Reload the module to pick up the cleared PYTHONPATH
            import importlib

            from logspark.Hooks import SparkRichHandler as shr_module

            importlib.reload(shr_module)

            handler = shr_module.SparkRichHandler()
            Console(file=io.StringIO())

            # Create a mock record with a long path
            record = Mock()
            record.pathname = "/very/long/path/to/project/module/file.py"
            record.funcName = "test_function"
            record.lineno = 42
            record.created = datetime.now().timestamp()

            # Mock get_level_text method
            handler.get_level_text = Mock(return_value="INFO")
            handler.enable_link_path = False

            # Create mock message renderable
            message_renderable = Text("Test message")

            # Call render method
            result = handler.render(
                record=record, traceback=None, message_renderable=message_renderable
            )

            # Should return a renderable
            assert result is not None

    def test_path_resolution_short_path(self):
        """Test path resolution with short path (less than 2 parts)"""
        handler = SparkRichHandler()

        # Create a mock record with short path
        record = Mock()
        record.pathname = "module.py"  # Single part path
        record.funcName = "test_function"
        record.lineno = 42
        record.created = datetime.now().timestamp()

        # Mock get_level_text method
        handler.get_level_text = Mock(return_value="INFO")
        handler.enable_link_path = False

        # Create mock message renderable
        message_renderable = Text("Test message")

        # Call render method
        result = handler.render(
            record=record, traceback=None, message_renderable=message_renderable
        )

        # Should return a renderable
        assert result is not None

    def test_path_resolution_two_parts(self):
        """Test path resolution with exactly 2 parts"""
        handler = SparkRichHandler()

        # Create a mock record with 2-part path
        record = Mock()
        record.pathname = "dir/module.py"  # Two part path
        record.funcName = "test_function"
        record.lineno = 42
        record.created = datetime.now().timestamp()

        # Mock get_level_text method
        handler.get_level_text = Mock(return_value="INFO")
        handler.enable_link_path = False

        # Create mock message renderable
        message_renderable = Text("Test message")

        # Call render method
        result = handler.render(
            record=record, traceback=None, message_renderable=message_renderable
        )

        # Should return a renderable
        assert result is not None

    def test_path_resolution_relative_path_error(self):
        """Test path resolution when relative_to raises ValueError"""
        test_pythonpath = "/different/path"
        test_record_path = "/completely/different/path/module.py"

        with patch.dict(os.environ, {"PYTHONPATH": test_pythonpath}):
            # Reload the module
            import importlib

            from logspark.Hooks import SparkRichHandler as shr_module

            importlib.reload(shr_module)

            handler = shr_module.SparkRichHandler()

            # Create a mock record
            record = Mock()
            record.pathname = test_record_path
            record.funcName = "test_function"
            record.lineno = 42
            record.created = datetime.now().timestamp()

            # Mock get_level_text method
            handler.get_level_text = Mock(return_value="INFO")
            handler.enable_link_path = False

            # Create mock message renderable
            message_renderable = Text("Test message")

            # Call render method - should handle ValueError gracefully
            result = handler.render(
                record=record, traceback=None, message_renderable=message_renderable
            )

            # Should return a renderable even when relative_to fails
            assert result is not None


class TestSparkRichHandlerRendering:
    """Test rendering functionality"""

    def test_render_without_traceback(self):
        """Test rendering log record without traceback"""
        handler = SparkRichHandler()
        handler.enable_link_path = False  # Disable link path to avoid URI issues

        # Create a real log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path/module.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Create message renderable
        message_renderable = Text("Test message")

        # Call render method
        result = handler.render(
            record=record, traceback=None, message_renderable=message_renderable
        )

        # Should return a Table from CustomLogRender
        from rich.table import Table

        assert isinstance(result, Table)

    def test_render_with_traceback(self):
        """Test rendering log record with traceback"""
        handler = SparkRichHandler()
        handler.enable_link_path = False  # Disable link path to avoid URI issues

        # Create a real log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="/test/path/module.py",
            lineno=42,
            msg="Test error",
            args=(),
            exc_info=None,
        )

        # Create message renderable and traceback
        message_renderable = Text("Test error message")

        # Create a mock traceback
        mock_traceback = Mock(spec=Traceback)

        # Call render method
        result = handler.render(
            record=record, traceback=mock_traceback, message_renderable=message_renderable
        )

        # Should return a Table
        from rich.table import Table

        assert isinstance(result, Table)

    def test_render_with_link_path_enabled(self):
        """Test rendering with link path enabled"""
        handler = SparkRichHandler()
        handler.enable_link_path = True

        # Use an absolute Windows path that will work with as_uri()
        import os

        test_path = os.path.abspath("test_module.py")

        # Create a real log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname=test_path,
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Create message renderable
        message_renderable = Text("Test message")

        # Call render method
        result = handler.render(
            record=record, traceback=None, message_renderable=message_renderable
        )

        # Should return a Table
        from rich.table import Table

        assert isinstance(result, Table)

    def test_render_with_formatter_datefmt(self):
        """Test rendering with formatter date format"""
        handler = SparkRichHandler()
        handler.enable_link_path = False  # Disable link path to avoid URI issues

        # Set up formatter with custom date format
        formatter = logging.Formatter(datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)

        # Create a real log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path/module.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Create message renderable
        message_renderable = Text("Test message")

        # Call render method
        result = handler.render(
            record=record, traceback=None, message_renderable=message_renderable
        )

        # Should return a Table
        from rich.table import Table

        assert isinstance(result, Table)

    def test_render_function_name_handling(self):
        """Test rendering with various function names"""
        handler = SparkRichHandler(show_function=True)
        handler.enable_link_path = False  # Disable link path to avoid URI issues

        # Test with normal function name
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path/module.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="test_function",
        )

        message_renderable = Text("Test message")

        result = handler.render(
            record=record, traceback=None, message_renderable=message_renderable
        )

        from rich.table import Table

        assert isinstance(result, Table)

    def test_render_with_empty_function_name(self):
        """Test rendering with empty function name"""
        handler = SparkRichHandler(show_function=True)
        handler.enable_link_path = False  # Disable link path to avoid URI issues

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path/module.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="",
        )

        message_renderable = Text("Test message")

        result = handler.render(
            record=record, traceback=None, message_renderable=message_renderable
        )

        from rich.table import Table

        assert isinstance(result, Table)


class TestSparkRichHandlerIntegration:
    """Integration tests for SparkRichHandler"""

    def test_full_logging_workflow(self):
        """Test complete logging workflow through SparkRichHandler"""
        # Create handler with string IO for testing
        test_stream = io.StringIO()
        console = Console(file=test_stream)
        handler = SparkRichHandler(console=console)

        # Create logger and add handler
        logger = logging.getLogger("test.integration")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        # Log various messages
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # Verify output was generated
        output = test_stream.getvalue()
        assert len(output) > 0
        assert "Info message" in output
        assert "Warning message" in output
        assert "Error message" in output

    def test_exception_logging_workflow(self):
        """Test exception logging through SparkRichHandler"""
        test_stream = io.StringIO()
        console = Console(file=test_stream)
        handler = SparkRichHandler(console=console, rich_tracebacks=True)

        logger = logging.getLogger("test.exception")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        # Log exception
        try:
            raise ValueError("Test exception for integration test")
        except ValueError:
            logger.exception("Exception occurred")

        # Verify output contains exception information
        output = test_stream.getvalue()
        assert len(output) > 0
        assert "Exception occurred" in output

    def test_handler_with_different_configurations(self):
        """Test handler with different show/hide configurations"""
        configurations = [
            {"show_time": True, "show_level": True, "show_path": True, "show_function": True},
            {"show_time": False, "show_level": False, "show_path": False, "show_function": False},
            {"show_time": True, "show_level": False, "show_path": True, "show_function": False},
        ]

        for config in configurations:
            test_stream = io.StringIO()
            console = Console(file=test_stream)
            handler = SparkRichHandler(console=console, **config)

            logger = logging.getLogger(f"test.config.{hash(str(config))}")
            logger.handlers.clear()  # Clear any existing handlers
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

            logger.info("Test message for configuration")

            output = test_stream.getvalue()
            assert len(output) > 0
            # Rich may wrap text, so check for key words instead of exact match
            assert (
                "Test" in output
                and "message" in output
                and ("configuration" in output or "configura" in output)
            )


class TestSparkRichHandlerEdgeCases:
    """Test edge cases and error conditions"""

    def test_render_with_none_values(self):
        """Test rendering with None values in record"""
        handler = SparkRichHandler()
        handler.enable_link_path = False  # Disable link path to avoid URI issues

        # Create record with None function name
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path/module.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.funcName = None

        message_renderable = Text("Test message")

        # Should handle None gracefully
        result = handler.render(
            record=record, traceback=None, message_renderable=message_renderable
        )

        from rich.table import Table

        assert isinstance(result, Table)

    def test_render_with_invalid_pathname(self):
        """Test rendering with invalid pathname"""
        handler = SparkRichHandler()
        handler.enable_link_path = False  # Disable link path to avoid URI issues

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="",  # Empty pathname
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        message_renderable = Text("Test message")

        # Should handle empty pathname gracefully
        result = handler.render(
            record=record, traceback=None, message_renderable=message_renderable
        )

        from rich.table import Table

        assert isinstance(result, Table)

    def test_render_with_zero_line_number(self):
        """Test rendering with zero line number"""
        handler = SparkRichHandler()
        handler.enable_link_path = False  # Disable link path to avoid URI issues

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path/module.py",
            lineno=0,  # Zero line number
            msg="Test message",
            args=(),
            exc_info=None,
        )

        message_renderable = Text("Test message")

        result = handler.render(
            record=record, traceback=None, message_renderable=message_renderable
        )

        from rich.table import Table

        assert isinstance(result, Table)

    def test_render_with_very_long_path(self):
        """Test rendering with very long pathname"""
        handler = SparkRichHandler()
        handler.enable_link_path = False  # Disable link path to avoid URI issues

        # Create very long path
        long_path = "/" + "/".join(["very_long_directory_name"] * 20) + "/module.py"

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname=long_path,
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        message_renderable = Text("Test message")

        result = handler.render(
            record=record, traceback=None, message_renderable=message_renderable
        )

        from rich.table import Table

        assert isinstance(result, Table)


# Property-Based Tests
from hypothesis import given
from hypothesis import strategies as st


class TestSparkRichHandlerProperties:
    """Property-based tests for SparkRichHandler"""

    @given(
        level=st.sampled_from([
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ]),
        message=st.text(min_size=1, max_size=500),
        pathname=st.one_of(
            st.just("/test/path/module.py"),
            st.just("C:\\test\\path\\module.py"),
            st.text(min_size=5, max_size=50).map(lambda x: f"/test/{x}.py"),
        ),
        lineno=st.integers(min_value=1, max_value=10000),
        function_name=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    )
    def test_property_render_always_succeeds(self, level, message, pathname, lineno, function_name):
        """
        For any valid log record parameters, render should always succeed and return a Table
        """
        handler = SparkRichHandler()
        handler.enable_link_path = False  # Disable link path to avoid URI issues

        # Create log record
        record = logging.LogRecord(
            name="test.logger",
            level=level,
            pathname=pathname,
            lineno=lineno,
            msg=message,
            args=(),
            exc_info=None,
        )

        if function_name is not None:
            record.funcName = function_name

        message_renderable = Text(message)

        # Should always succeed
        result = handler.render(
            record=record, traceback=None, message_renderable=message_renderable
        )

        from rich.table import Table

        assert isinstance(result, Table)

    @given(
        show_time=st.booleans(),
        show_level=st.booleans(),
        show_path=st.booleans(),
        show_function=st.booleans(),
        message=st.text(min_size=1, max_size=200),
    )
    def test_property_configuration_consistency(
        self, show_time, show_level, show_path, show_function, message
    ):
        """

        For any configuration, the handler should consistently apply settings to CustomLogRender

        """
        handler = SparkRichHandler(
            show_time=show_time,
            show_level=show_level,
            show_path=show_path,
            show_function=show_function,
        )
        handler.enable_link_path = False  # Disable link path to avoid URI issues

        # Verify configuration was applied to CustomLogRender
        assert handler._c_log_render.show_time == show_time
        assert handler._c_log_render.show_level == show_level
        assert handler._c_log_render.show_path == show_path
        assert handler._c_log_render.show_function == show_function

        # Test that rendering works with this configuration
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path/module.py",
            lineno=42,
            msg=message,
            args=(),
            exc_info=None,
        )

        message_renderable = Text(message)

        result = handler.render(
            record=record, traceback=None, message_renderable=message_renderable
        )

        from rich.table import Table

        assert isinstance(result, Table)

    @given(
        pathname=st.text(min_size=1, max_size=300),
        lineno=st.integers(min_value=0, max_value=100000),
    )
    def test_property_path_resolution_robustness(self, pathname, lineno):
        """

        For any pathname and line number, path resolution should handle gracefully

        """
        handler = SparkRichHandler()
        handler.enable_link_path = False  # Disable link path to avoid URI issues

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname=pathname,
            lineno=lineno,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        message_renderable = Text("Test message")

        # Should handle any pathname/lineno combination without error
        result = handler.render(
            record=record, traceback=None, message_renderable=message_renderable
        )

        from rich.table import Table

        assert isinstance(result, Table)

    @given(
        time_format=st.sampled_from([
            "%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "[%x %X]",
            "%H:%M",
            "Custom: %H:%M",
        ]),
        message=st.text(min_size=1, max_size=100),
    )
    def test_property_time_format_handling(self, time_format, message):
        """

        For any time format, the handler should pass it correctly to CustomLogRender

        """
        handler = SparkRichHandler(show_time=True, log_time_format=time_format)
        handler.enable_link_path = False  # Disable link path to avoid URI issues

        # Verify time format was set
        assert handler._c_log_render.time_format == time_format

        # Test rendering with this time format
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path/module.py",
            lineno=42,
            msg=message,
            args=(),
            exc_info=None,
        )

        message_renderable = Text(message)

        result = handler.render(
            record=record, traceback=None, message_renderable=message_renderable
        )

        from rich.table import Table

        assert isinstance(result, Table)

    @given(has_traceback=st.booleans(), message=st.text(min_size=1, max_size=200))
    def test_property_traceback_handling(self, has_traceback, message):
        """

        For any message with or without traceback, rendering should succeed

        """
        handler = SparkRichHandler()
        handler.enable_link_path = False  # Disable link path to avoid URI issues

        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="/test/path/module.py",
            lineno=42,
            msg=message,
            args=(),
            exc_info=None,
        )

        message_renderable = Text(message)
        traceback = Mock(spec=Traceback) if has_traceback else None

        result = handler.render(
            record=record, traceback=traceback, message_renderable=message_renderable
        )

        from rich.table import Table

        assert isinstance(result, Table)
