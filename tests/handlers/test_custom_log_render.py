"""
Test CustomLogRender component for Rich-based log formatting.

Tests validate:
- Table grid generation with proper columns and styling
- Time rendering with omit_repeated_times functionality
- Path rendering with line numbers and links
- Function name rendering with proper formatting
- Level styling application
- Message rendering with proper overflow handling
"""

import io
from datetime import datetime

import pytest

# Skip entire module if Rich is not available
pytest.importorskip("rich")

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
            show_function=True,
            time_format="%H:%M:%S",
            omit_repeated_times=False,
            level_width=10,
        )

        assert renderer.show_time is False
        assert renderer.show_level is True
        assert renderer.show_path is False
        assert renderer.show_function is True
        assert renderer.time_format == "%H:%M:%S"
        assert renderer.omit_repeated_times is False
        assert renderer.level_width == 10

    def test_callable_time_format(self):
        """Test CustomLogRender with callable time format"""

        def custom_time_format(dt):
            return Text(f"Custom: {dt.strftime('%H:%M')}")

        renderer = CustomLogRender(time_format=custom_time_format)
        assert callable(renderer.time_format)


class TestCustomLogRenderTableGeneration:
    """Test table generation with different configurations"""

    def test_minimal_table_generation(self):
        """Test table generation with minimal configuration"""
        renderer = CustomLogRender(
            show_time=False, show_level=False, show_path=False, show_function=False
        )

        console = Console(file=io.StringIO())
        renderables = [Text("Test message")]

        table = renderer(console, renderables)

        assert isinstance(table, Table)
        # Should have arrow column and message column at minimum
        assert len(table.columns) >= 2

    def test_full_table_generation(self):
        """Test table generation with all features enabled"""
        renderer = CustomLogRender(
            show_time=True, show_level=True, show_path=True, show_function=True
        )

        console = Console(file=io.StringIO())
        renderables = [Text("Test message")]

        table = renderer(
            console,
            renderables,
            log_time=datetime.now(),
            level="INFO",
            path="/test/path.py",
            line_no=42,
            function_name="test_function",
        )

        assert isinstance(table, Table)
        # Should have time, spacer, level, divider, path, divider, function, arrow, message
        assert len(table.columns) >= 7

    def test_table_with_link_path(self):
        """Test table generation with link path"""
        renderer = CustomLogRender(show_path=True)

        console = Console(file=io.StringIO())
        renderables = [Text("Test message")]

        table = renderer(
            console, renderables, path="/test/path.py", line_no=42, link_path="file:///test/path.py"
        )

        assert isinstance(table, Table)
        # Verify table was created successfully
        assert len(table.columns) >= 2


class TestCustomLogRenderTimeHandling:
    """Test time rendering functionality"""

    def test_time_rendering_with_default_format(self):
        """Test time rendering with default format"""
        renderer = CustomLogRender(show_time=True)
        console = Console(file=io.StringIO())

        test_time = datetime(2023, 12, 25, 14, 30, 45)

        time_text = renderer._render_time(console, test_time, None)

        assert isinstance(time_text, Text)
        assert len(str(time_text)) > 0
        # Should contain date/time information
        assert "12/25/23" in str(time_text) or "2023" in str(time_text)

    def test_time_rendering_with_custom_format(self):
        """Test time rendering with custom format"""
        renderer = CustomLogRender(show_time=True)
        console = Console(file=io.StringIO())

        test_time = datetime(2023, 12, 25, 14, 30, 45)
        custom_format = "%H:%M:%S"

        time_text = renderer._render_time(console, test_time, custom_format)

        assert isinstance(time_text, Text)
        assert "14:30:45" in str(time_text)

    def test_time_rendering_with_callable_format(self):
        """Test time rendering with callable format"""

        def custom_formatter(dt):
            return Text(f"Custom: {dt.hour:02d}:{dt.minute:02d}")

        renderer = CustomLogRender(show_time=True, time_format=custom_formatter)
        console = Console(file=io.StringIO())

        test_time = datetime(2023, 12, 25, 14, 30, 45)

        time_text = renderer._render_time(console, test_time, custom_formatter)

        assert isinstance(time_text, Text)
        assert "Custom: 14:30" in str(time_text)

    def test_omit_repeated_times_functionality(self):
        """Test omit_repeated_times functionality"""
        renderer = CustomLogRender(show_time=True, omit_repeated_times=True)
        console = Console(file=io.StringIO())

        test_time = datetime(2023, 12, 25, 14, 30, 45)

        # First call should show time
        first_render = renderer._render_time(console, test_time, "%H:%M:%S")
        assert "14:30:45" in str(first_render)

        # Second call with same time should show spaces
        second_render = renderer._render_time(console, test_time, "%H:%M:%S")
        # Should be mostly spaces (omitted)
        assert str(second_render).strip() == "" or str(second_render).isspace()

        # Different time should show again
        different_time = datetime(2023, 12, 25, 14, 31, 0)
        third_render = renderer._render_time(console, different_time, "%H:%M:%S")
        assert "14:31:00" in str(third_render)

    def test_omit_repeated_times_disabled(self):
        """Test behavior when omit_repeated_times is disabled"""
        renderer = CustomLogRender(show_time=True, omit_repeated_times=False)
        console = Console(file=io.StringIO())

        test_time = datetime(2023, 12, 25, 14, 30, 45)

        # Both calls should show time
        first_render = renderer._render_time(console, test_time, "%H:%M:%S")
        second_render = renderer._render_time(console, test_time, "%H:%M:%S")

        assert "14:30:45" in str(first_render)
        assert "14:30:45" in str(second_render)


class TestCustomLogRenderPathHandling:
    """Test path rendering functionality"""

    def test_path_rendering_basic(self):
        """Test basic path rendering"""
        renderer = CustomLogRender()

        path_text = renderer._render_path("/test/path.py", None, None)

        assert isinstance(path_text, Text)
        assert "/test/path.py" in str(path_text)

    def test_path_rendering_with_line_number(self):
        """Test path rendering with line number"""
        renderer = CustomLogRender()

        path_text = renderer._render_path("/test/path.py", 42, None)

        assert isinstance(path_text, Text)
        assert "/test/path.py" in str(path_text)
        assert "42" in str(path_text)
        assert ":" in str(path_text)  # Should have colon separator

    def test_path_rendering_with_link(self):
        """Test path rendering with link path"""
        renderer = CustomLogRender()

        path_text = renderer._render_path("/test/path.py", 42, "file:///test/path.py")

        assert isinstance(path_text, Text)
        assert "/test/path.py" in str(path_text)
        assert "42" in str(path_text)

    def test_path_rendering_link_only(self):
        """Test path rendering with link but no line number"""
        renderer = CustomLogRender()

        path_text = renderer._render_path("/test/path.py", None, "file:///test/path.py")

        assert isinstance(path_text, Text)
        assert "/test/path.py" in str(path_text)


class TestCustomLogRenderFunctionHandling:
    """Test function name rendering functionality"""

    def test_function_rendering_basic(self):
        """Test basic function name rendering"""
        renderer = CustomLogRender()

        function_text = renderer._render_function_("test_function")

        assert isinstance(function_text, Text)
        assert "test_function" in str(function_text)
        assert "[" in str(function_text)
        assert "]" in str(function_text)

    def test_function_rendering_empty(self):
        """Test function rendering with empty name"""
        renderer = CustomLogRender()

        function_text = renderer._render_function_(None)
        assert isinstance(function_text, Text)
        assert str(function_text) == ""

        function_text = renderer._render_function_("")
        assert isinstance(function_text, Text)
        assert str(function_text) == ""

        function_text = renderer._render_function_("   ")
        assert isinstance(function_text, Text)
        assert str(function_text) == ""

    def test_function_rendering_with_whitespace(self):
        """Test function rendering with whitespace"""
        renderer = CustomLogRender()

        function_text = renderer._render_function_("  test_function  ")

        assert isinstance(function_text, Text)
        assert "test_function" in str(function_text)
        assert "[" in str(function_text)
        assert "]" in str(function_text)


class TestCustomLogRenderLevelStyling:
    """Test level styling functionality"""

    def test_get_level_style_standard_levels(self):
        """Test level styling for standard log levels"""
        renderer = CustomLogRender()

        # Test standard levels
        debug_style = renderer._get_level_style("DEBUG")
        info_style = renderer._get_level_style("INFO")
        warning_style = renderer._get_level_style("WARNING")
        error_style = renderer._get_level_style("ERROR")
        critical_style = renderer._get_level_style("CRITICAL")

        # All should return Style objects (not null)
        assert debug_style is not None
        assert info_style is not None
        assert warning_style is not None
        assert error_style is not None
        assert critical_style is not None

    def test_get_level_style_message_variants(self):
        """Test level styling for message variants"""
        renderer = CustomLogRender()

        # Test message variants
        debug_msg_style = renderer._get_level_style("DEBUG", message=True)
        info_msg_style = renderer._get_level_style("INFO", message=True)
        warning_msg_style = renderer._get_level_style("WARNING", message=True)

        assert debug_msg_style is not None
        assert info_msg_style is not None
        assert warning_msg_style is not None

    def test_get_level_style_unknown_level(self):
        """Test level styling for unknown levels"""
        renderer = CustomLogRender()

        unknown_style = renderer._get_level_style("UNKNOWN")
        assert unknown_style is not None  # Should return Style.null()

    def test_get_level_style_text_object(self):
        """Test level styling with Text object input"""
        renderer = CustomLogRender()

        text_level = Text("INFO")
        style = renderer._get_level_style(text_level)
        assert style is not None

    def test_get_level_style_with_whitespace(self):
        """Test level styling with whitespace"""
        renderer = CustomLogRender()

        style = renderer._get_level_style("  INFO  ")
        assert style is not None


class TestCustomLogRenderDividerHandling:
    """Test divider functionality"""

    def test_add_divider_static_method(self):
        """Test add_divider static method"""
        from rich.style import Style

        table = Table.grid()
        row = []
        level_style = Style(color="red")
        original_row_length = len(row)

        new_table, new_row = CustomLogRender.add_divider(table, row, level_style)

        assert new_table is table  # Should return same table
        assert len(new_row) == original_row_length + 1  # Should add one item to row
        assert isinstance(new_row[-1], Text)  # Last item should be Text
        assert "-" in str(new_row[-1])  # Should contain divider character


class TestCustomLogRenderIntegration:
    """Integration tests for CustomLogRender"""

    def test_complete_rendering_workflow(self):
        """Test complete rendering workflow with all features"""
        renderer = CustomLogRender(
            show_time=True, show_level=True, show_path=True, show_function=True
        )

        console = Console(file=io.StringIO())
        renderables = [Text("Test log message")]

        table = renderer(
            console,
            renderables,
            log_time=datetime(2023, 12, 25, 14, 30, 45),
            level="INFO",
            path="/test/module.py",
            line_no=123,
            link_path="file:///test/module.py",
            function_name="test_function",
        )

        assert isinstance(table, Table)
        assert len(table.columns) > 0

        # Render the table to verify it works
        console.print(table)
        output = console.file.getvalue()
        assert len(output) > 0

    def test_rendering_with_multiple_renderables(self):
        """Test rendering with multiple renderables (message + traceback)"""
        renderer = CustomLogRender()

        console = Console(file=io.StringIO())
        renderables = [Text("Error message"), Text("Traceback information")]

        table = renderer(console, renderables, level="ERROR")

        assert isinstance(table, Table)

        # Render to verify
        console.print(table)
        output = console.file.getvalue()
        assert len(output) > 0

    def test_rendering_with_no_optional_parameters(self):
        """Test rendering with minimal parameters"""
        renderer = CustomLogRender()

        console = Console(file=io.StringIO())
        renderables = [Text("Simple message")]

        table = renderer(console, renderables)

        assert isinstance(table, Table)

        # Should work without optional parameters
        console.print(table)
        output = console.file.getvalue()
        assert len(output) > 0


# Property-Based Tests
from hypothesis import given
from hypothesis import strategies as st


class TestCustomLogRenderProperties:
    """Property-based tests for CustomLogRender"""

    @given(
        message=st.text(min_size=1, max_size=500),
        show_time=st.booleans(),
        show_level=st.booleans(),
        show_path=st.booleans(),
        show_function=st.booleans(),
    )
    def test_property_table_generation_always_succeeds(
        self, message, show_time, show_level, show_path, show_function
    ):
        """

        For any configuration and message, CustomLogRender should always generate a valid Table

        """
        renderer = CustomLogRender(
            show_time=show_time,
            show_level=show_level,
            show_path=show_path,
            show_function=show_function,
        )

        console = Console(file=io.StringIO())
        renderables = [Text(message)]

        # Should always succeed in generating a table
        table = renderer(console, renderables)

        assert isinstance(table, Table)
        assert len(table.columns) >= 2  # At minimum: arrow + message

        # Should be renderable without error
        console.print(table)
        output = console.file.getvalue()
        assert len(output) > 0

    @given(level=st.text(min_size=1, max_size=20), message_flag=st.booleans())
    def test_property_level_styling_always_returns_style(self, level, message_flag):
        """

        For any level string, _get_level_style should always return a Style object

        """
        renderer = CustomLogRender()

        style = renderer._get_level_style(level, message=message_flag)

        # Should always return a Style object (never None)
        assert style is not None
        from rich.style import Style

        assert isinstance(style, Style)

    @given(
        path=st.text(min_size=1, max_size=200).filter(lambda x: x.isprintable() and x.strip()),
        line_no=st.one_of(st.none(), st.integers(min_value=1, max_value=10000)),
    )
    def test_property_path_rendering_always_succeeds(self, path, line_no):
        """

        For any path and line number, _render_path should always return valid Text

        """
        renderer = CustomLogRender()

        path_text = renderer._render_path(path, line_no, None)

        assert isinstance(path_text, Text)
        # Rich may filter out some characters, so check if path content is preserved
        path_str = str(path_text)
        assert len(path_str) > 0  # Should produce some output
        # Check that at least some part of the path is preserved
        assert any(char in path_str for char in path if char.isprintable())

        if line_no is not None:
            assert str(line_no) in path_str

    @given(
        function_name=st.one_of(
            st.none(), st.text(min_size=0, max_size=100).filter(lambda x: x.isprintable())
        )
    )
    def test_property_function_rendering_handles_all_inputs(self, function_name):
        """

        For any function name (including None and empty), _render_function_ should handle gracefully

        """
        renderer = CustomLogRender()

        function_text = renderer._render_function_(function_name)

        assert isinstance(function_text, Text)

        if function_name and function_name.strip():
            # Non-empty function names should appear in output with brackets
            function_str = str(function_text)
            assert "[" in function_str
            assert "]" in function_str
            # Check that at least some part of the function name is preserved
            assert any(char in function_str for char in function_name.strip() if char.isprintable())
        else:
            # Empty or None function names should produce empty text
            assert str(function_text) == ""

    @given(
        time_format=st.sampled_from(["%H:%M:%S", "%Y-%m-%d %H:%M", "[%x %X]", "%H:%M"]),
        omit_repeated=st.booleans(),
    )
    def test_property_time_rendering_consistency(self, time_format, omit_repeated):
        """

        For any time format and omit setting, time rendering should be consistent

        """
        renderer = CustomLogRender(
            show_time=True, time_format=time_format, omit_repeated_times=omit_repeated
        )

        console = Console(file=io.StringIO())
        test_time = datetime(2023, 12, 25, 14, 30, 45)

        # First render
        first_render = renderer._render_time(console, test_time, time_format)
        assert isinstance(first_render, Text)
        assert len(str(first_render)) > 0

        # Second render with same time
        second_render = renderer._render_time(console, test_time, time_format)
        assert isinstance(second_render, Text)

        if omit_repeated:
            # When omit_repeated is True, second render should be different (spaces)
            # unless the format produces empty output
            if len(str(first_render).strip()) > 0:
                # Second should be mostly spaces or empty
                second_content = str(second_render)
                assert (
                    second_content.isspace()
                    or second_content == ""
                    or len(second_content.strip()) == 0
                )
        else:
            # When omit_repeated is False, both should be the same
            assert str(first_render) == str(second_render)
