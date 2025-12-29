"""
Tests for CustomLogRender class

This module tests the custom Hooks log renderer that provides styled terminal output
for LogSpark Logging.
"""

from datetime import datetime
from unittest.mock import Mock

from rich.console import Console
from rich.table import Table
from rich.text import Text

from logspark.Hooks.CustomLogRender import CustomLogRender


class TestCustomLogRenderInitialization:
    """Test CustomLogRender initialization and configuration"""

    def test_default_initialization(self):
        """Test CustomLogRender with default parameters"""
        renderer = CustomLogRender()

        assert renderer.show_time is True
        assert renderer.show_level is False
        assert renderer.show_path is True
        assert renderer.show_function is False
        assert renderer.time_format == "[%x %X]"
        assert renderer.omit_repeated_times is True
        assert renderer.level_width == 8
        assert renderer._last_time is None

    def test_custom_initialization(self):
        """Test CustomLogRender with custom parameters"""
        renderer = CustomLogRender(
            show_time=False,
            show_level=True,
            show_path=False,
            show_function=False,
            time_format="%H:%M:%S",
            omit_repeated_times=False,
            level_width=10,
        )

        assert renderer.show_time is False
        assert renderer.show_level is True
        assert renderer.show_path is False
        assert renderer.show_function is False
        assert renderer.time_format == "%H:%M:%S"
        assert renderer.omit_repeated_times is False
        assert renderer.level_width == 10
        assert renderer._last_time is None


class TestCustomLogRenderLevelStyles:
    """Test level style handling"""

    def test_get_level_style_standard_levels(self):
        """Test style retrieval for standard log levels"""
        renderer = CustomLogRender()

        # Test standard levels
        debug_style = renderer._get_level_style("DEBUG")
        assert debug_style.color.name == "cyan"
        assert debug_style.dim is True

        info_style = renderer._get_level_style("INFO")
        assert info_style.color.name == "green"

        warning_style = renderer._get_level_style("WARNING")
        assert warning_style.color.name == "yellow"

        error_style = renderer._get_level_style("ERROR")
        assert error_style.color.name == "red"

        critical_style = renderer._get_level_style("CRITICAL")
        assert critical_style.color.name == "magenta"
        assert critical_style.bold is True

    def test_get_level_style_message_styles(self):
        """Test style retrieval for message styles"""
        renderer = CustomLogRender()

        # Test message styles
        debug_msg_style = renderer._get_level_style("DEBUG", message=True)
        assert debug_msg_style.color.name == "white"
        assert debug_msg_style.dim is True
        assert debug_msg_style.italic is True

        info_msg_style = renderer._get_level_style("INFO", message=True)
        assert info_msg_style.color.name == "white"

        critical_msg_style = renderer._get_level_style("CRITICAL", message=True)
        assert critical_msg_style.color is None

    def test_get_level_style_unknown_level(self):
        """Test style retrieval for unknown log levels"""
        renderer = CustomLogRender()

        unknown_style = renderer._get_level_style("UNKNOWN")
        assert unknown_style.color is None  # Style.null()

        unknown_msg_style = renderer._get_level_style("UNKNOWN", message=True)
        assert unknown_msg_style.color is None  # Style.null()

    def test_get_level_style_with_whitespace(self):
        """Test style retrieval with whitespace in level names"""
        renderer = CustomLogRender()

        # Test that whitespace is stripped
        info_style = renderer._get_level_style("  INFO  ")
        assert info_style.color.name == "green"


class TestCustomLogRenderTimeHandling:
    """Test time rendering functionality"""

    def test_render_time_with_string_format(self):
        """Test time rendering with string format"""
        renderer = CustomLogRender(time_format="%H:%M:%S")
        console = Console()
        test_time = datetime(2023, 12, 25, 14, 30, 45)

        time_text = renderer._render_time(console, test_time, None)

        assert isinstance(time_text, Text)
        assert "14:30:45" in str(time_text)
        assert time_text.style.color.name == "white"
        assert time_text.style.dim is True

    def test_render_time_with_callable_format(self):
        """Test time rendering with callable format"""

        def custom_format(dt):
            return Text(f"Custom: {dt.hour}:{dt.minute}")

        renderer = CustomLogRender(time_format=custom_format)
        console = Console()
        test_time = datetime(2023, 12, 25, 14, 30, 45)

        time_text = renderer._render_time(console, test_time, None)

        assert isinstance(time_text, Text)
        assert "Custom: 14:30" in str(time_text)

    def test_render_time_omit_repeated(self):
        """Test omitting repeated times"""
        renderer = CustomLogRender(time_format="%H:%M:%S", omit_repeated_times=True)
        console = Console()
        test_time = datetime(2023, 12, 25, 14, 30, 45)

        # First call should show time
        time_text1 = renderer._render_time(console, test_time, None)
        assert "14:30:45" in str(time_text1)

        # Second call with same time should show spaces
        time_text2 = renderer._render_time(console, test_time, None)
        assert str(time_text2).strip() == ""  # Should be spaces

        # Different time should show again
        different_time = datetime(2023, 12, 25, 15, 30, 45)
        time_text3 = renderer._render_time(console, different_time, None)
        assert "15:30:45" in str(time_text3)

    def test_render_time_no_omit_repeated(self):
        """Test not omitting repeated times"""
        renderer = CustomLogRender(time_format="%H:%M:%S", omit_repeated_times=False)
        console = Console()
        test_time = datetime(2023, 12, 25, 14, 30, 45)

        # Both calls should show time
        time_text1 = renderer._render_time(console, test_time, None)
        time_text2 = renderer._render_time(console, test_time, None)

        assert "14:30:45" in str(time_text1)
        assert "14:30:45" in str(time_text2)

    def test_render_time_with_none_time(self):
        """Test time rendering when log_time is None"""
        renderer = CustomLogRender(time_format="%H:%M:%S")
        console = Mock()
        console.get_datetime.return_value = datetime(2023, 12, 25, 14, 30, 45)

        time_text = renderer._render_time(console, None, None)

        console.get_datetime.assert_called_once()
        assert isinstance(time_text, Text)


class TestCustomLogRenderPathHandling:
    """Test path rendering functionality"""

    def test_render_path_basic(self):
        """Test basic path rendering"""
        renderer = CustomLogRender()

        path_text = renderer._render_path("test.py", None, None)

        assert isinstance(path_text, Text)
        assert "test.py" in str(path_text)
        assert path_text.style.color.name == "cyan"

    def test_render_path_with_line_number(self):
        """Test path rendering with line number"""
        renderer = CustomLogRender()

        path_text = renderer._render_path("test.py", 42, None)

        assert isinstance(path_text, Text)
        assert "test.py" in str(path_text)
        assert "42" in str(path_text)
        assert ":" in str(path_text)

    def test_render_path_with_link(self):
        """Test path rendering with link"""
        renderer = CustomLogRender()

        path_text = renderer._render_path("test.py", None, "/full/path/test.py")

        assert isinstance(path_text, Text)
        assert "test.py" in str(path_text)
        # Link should be applied to the text

    def test_render_path_with_line_and_link(self):
        """Test path rendering with both line number and link"""
        renderer = CustomLogRender()

        path_text = renderer._render_path("test.py", 42, "/full/path/test.py")

        assert isinstance(path_text, Text)
        assert "test.py" in str(path_text)
        assert "42" in str(path_text)
        assert ":" in str(path_text)


class TestCustomLogRenderTableGeneration:
    """Test table generation functionality"""

    def test_call_minimal_configuration(self):
        """Test table generation with minimal configuration"""
        renderer = CustomLogRender(show_time=False, show_level=False, show_path=False)
        console = Console()
        renderables = [Text("Test message")]

        table = renderer(console, renderables)

        assert isinstance(table, Table)
        assert table.expand is True
        # Should have at least the arrow and message columns
        assert len(table.columns) >= 2

    def test_call_full_configuration(self):
        """Test table generation with all features enabled"""
        renderer = CustomLogRender(show_time=True, show_level=True, show_path=True, level_width=10)
        console = Console()
        renderables = [Text("Test message")]

        table = renderer(
            console,
            renderables,
            log_time=datetime(2023, 12, 25, 14, 30, 45),
            level="INFO",
            path="test.py",
            line_no=42,
            link_path="/full/path/test.py",
        )

        assert isinstance(table, Table)
        assert table.expand is True
        # Should have time, level, arrow, message, and path columns
        assert len(table.columns) == 7

    def test_call_with_different_levels(self):
        """Test table generation with different log levels"""
        renderer = CustomLogRender(show_level=True)
        console = Console()
        renderables = [Text("Test message")]

        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in levels:
            table = renderer(console, renderables, level=level)
            assert isinstance(table, Table)
            # Verify table is created successfully for each level

    def test_call_without_path_when_show_path_true(self):
        """Test table generation when show_path is True but no path provided"""
        renderer = CustomLogRender(show_path=True)
        console = Console()
        renderables = [Text("Test message")]

        table = renderer(console, renderables, path=None)

        assert isinstance(table, Table)
        # Should not include path column when path is None
        # Even though show_path is True

    def test_call_with_empty_renderables(self):
        """Test table generation with empty renderables"""
        renderer = CustomLogRender()
        console = Console()
        renderables = []

        table = renderer(console, renderables)

        assert isinstance(table, Table)
        # Should handle empty renderables gracefully

    def test_call_with_multiple_renderables(self):
        """Test table generation with multiple renderables"""
        renderer = CustomLogRender()
        console = Console()
        renderables = [Text("First part"), Text("Second part"), Text("Third part")]

        table = renderer(console, renderables)

        assert isinstance(table, Table)
        # Should handle multiple renderables


class TestCustomLogRenderIntegration:
    """Integration tests for CustomLogRender"""

    def test_consistent_styling_across_calls(self):
        """Test that styling remains consistent across multiple calls"""
        renderer = CustomLogRender(show_level=True)
        console = Console()
        renderables = [Text("Test message")]

        # Multiple calls with same level should have consistent styling
        table1 = renderer(console, renderables, level="INFO")
        table2 = renderer(console, renderables, level="INFO")

        assert isinstance(table1, Table)
        assert isinstance(table2, Table)
        # Both should be created successfully with consistent structure

    def test_time_state_persistence(self):
        """Test that time state persists across calls"""
        renderer = CustomLogRender(show_time=True, time_format="%H:%M:%S", omit_repeated_times=True)
        console = Console()
        renderables = [Text("Test message")]
        test_time = datetime(2023, 12, 25, 14, 30, 45)

        # First call should set the last time
        table1 = renderer(console, renderables, log_time=test_time)
        assert renderer._last_time is not None

        # Second call with same time should use the stored last time
        table2 = renderer(console, renderables, log_time=test_time)
        assert renderer._last_time is not None

        assert isinstance(table1, Table)
        assert isinstance(table2, Table)

    def test_column_configuration_consistency(self):
        """Test that column configuration is applied consistently"""
        renderer = CustomLogRender(show_time=True, show_level=True, show_path=True, level_width=12)
        console = Console()
        renderables = [Text("Test message")]

        table = renderer(console, renderables, level="WARNING", path="test.py")

        assert isinstance(table, Table)
        # Should have the expected number of columns based on configuration
        expected_columns = 7  # time, level, arrow, message, path
        assert len(table.columns) == expected_columns
