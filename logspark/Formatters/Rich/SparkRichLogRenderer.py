import math
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import List

from rich._log_render import FormatTimeCallable
from rich.console import Console, ConsoleRenderable, RenderableType
from rich.containers import Renderables
from rich.pretty import Pretty
from rich.style import Style
from rich.table import Table
from rich.text import Text, TextType


class SparkRichLogRenderer:
    """
    Custom log renderer with budget-based column layout for Rich console output.

    Provides structured, terminal-aware log rendering that adapts to available
    screen space while maintaining readability. Uses a priority-based width
    allocation strategy to ensure message content is always visible.

    Features:
        - Budget-based column width allocation
        - Configurable display of time, level, path, and function columns
        - Automatic column collapse under space constraints
        - Message column always receives priority for width allocation
        - Rich styling with consistent color scheme

    Layout Strategy:
        1. Fixed columns (time, level, arrow) allocated first
        2. Message column guaranteed minimum width
        3. Optional metadata columns (path, function) allocated from remaining space
        4. Columns collapse gracefully when terminal width is insufficient

    Args:
        show_time: Whether to display timestamps (default: True)
        show_level: Whether to display log levels (default: False)
        show_path: Whether to display source file paths (default: True)
        show_function: Whether to display function names (default: False)
        time_format: Time format string or callable (default: "[%x %X]")
        omit_repeated_times: Whether to hide repeated timestamps (default: True)
        level_width: Fixed width for level column (default: 8)
        max_path_width: Maximum width for path column (default: 40)
        max_function_width: Maximum width for function column (default: 25)
        min_message_width: Minimum width reserved for log messages (default: 60)
    """

    _layout_degradation_flag: bool = False
    _TIME_STYLE = Style(color="white", dim=True)
    _PATH_STYLE = Style(color="cyan")
    _FUNCTION_STYLE = Style(color="white", dim=True)
    _INDENT_STYLE = Style(color="white", dim=True)
    _LEVEL_STYLES = {
        "DEBUG": Style(color="cyan", dim=True),
        "INFO": Style(color="green"),
        "WARNING": Style(color="yellow"),
        "ERROR": Style(color="red"),
        "CRITICAL": Style(color="magenta", bold=True),
        "MESSAGE_DEBUG": Style(color="white", dim=True, italic=True),
        "MESSAGE_INFO": Style(color="white"),
        "MESSAGE_WARNING": Style.null(),
        "MESSAGE_ERROR": Style(color="red"),
        "MESSAGE_CRITICAL": Style(color="magenta"),
    }

    # noinspection PyMissingConstructor
    def __init__(
        self,
        *,
        show_time: bool = True,
        show_level: bool = False,
        show_path: bool = True,
        show_function: bool = False,
        time_format: str | FormatTimeCallable = "[%x %X]",
        omit_repeated_times: bool = True,
        level_width: int = 8,
        max_path_width: int = 40,
        max_function_width: int = 25,
        min_message_width: int = 40,
    ) -> None:
        self.show_time = show_time
        self.show_level = show_level
        self.show_path = show_path
        self.show_function = show_function
        self.time_format = time_format
        self.omit_repeated_times = omit_repeated_times
        self.level_width = level_width

        self.max_path_width = max_path_width
        self.max_function_width = max_function_width
        self.min_message_width = min_message_width

        self._last_time: Text | None = None
        self._minimal_col_width: int = 10
        self._right_gutter: int = 4

    def __call__(
        self,
        console: Console,
        renderables: Iterable[ConsoleRenderable],
        *,
        log_time: datetime | None = None,
        time_format: str | FormatTimeCallable | None = None,
        level: TextType = "",
        path: Path | None = None,
        line_no: int | None = None,
        link_path: str | None = None,
        function_name: str | None = None,
    ) -> ConsoleRenderable:
        """
        Render a single log record as a Rich Table row using a budgeted, non-expanding layout.

        Layout model:
            - The terminal is treated as a finite-width surface.
            - Fixed-priority columns (time, level, arrow) are allocated first.
            - The message column is guaranteed a minimum width and always wins space conflicts.
            - Optional metadata columns (path, function) are allocated last and may collapse to zero.
            - No column width is inferred by Rich at render time.

        Column order (left → right):
            1. Time (optional, width grows monotonically to max observed format width)
            2. Level (optional, fixed width)
            3. Arrow separator (optional, fixed width, collapsible under pressure)
            4. Message (required, folded, highest priority)
            5. Path (optional, right-aligned, collapsible)
            6. Function (optional, right-aligned, collapsible)

        Invariants:
            - `expand=False` is enforced to prevent Rich from reflowing columns.
            - Column widths are computed before rendering and passed explicitly.
            - The message column always retains at least `min_message_width` if possible.
            - When space is insufficient, optional metadata columns collapse before the message.

        Args:
            console:
                Active Rich Console used for size introspection.
            renderables:
                Renderables that form the log message body.
            log_time:
                Timestamp for the log record.
            time_format:
                Optional override for timestamp formatting.
            level:
                Log level name or Text.
            path:
                Source file path.
            line_no:
                Source line number.
            link_path:
                Optional link target for path rendering.
            function_name:
                Calling function name.

        Returns:
            A Rich Table containing exactly one rendered log row.
        """
        table = Table.grid(padding=(0, 1), expand=False)
        level_style = self._get_level_style(level)
        message_style = self._get_level_style(level, message=True)
        row: list[RenderableType] = []

        # Create Renderables
        if self.show_time:
            time_renderable = self._render_time(console, log_time, time_format)
        else:
            time_renderable = None
        if self.show_level:
            level_display = str(level).strip() if hasattr(level, "plain") else str(level).strip()
            level_renderable = Text(level_display, style=level_style)
        else:
            level_renderable = None
        if self.show_path and path:
            path_renderable = self._render_path(path, line_no, link_path)
        else:
            path_renderable = None

        if self.show_function and function_name:
            function_renderable = self._render_function_(function_name, path_renderable)
        else:
            function_renderable = None

        # Set the Variable Widths
        message_width, path_width, function_width, show_arrow = self._assign_variable_widths(
            console, time_renderable, level_renderable, path_renderable, function_renderable
        )

        # Create Table
        if time_renderable is not None:
            if self._last_time is not None:
                table.add_column(
                    style=self._TIME_STYLE,
                    width=max(self._last_time.cell_len, time_renderable.cell_len),
                    justify="left",
                )
            else:
                table.add_column(
                    style=self._TIME_STYLE, width=time_renderable.cell_len, justify="left"
                )
            row.append(time_renderable)
        if level_renderable is not None:
            table.add_column(width=self.level_width, style=level_style, justify="left")
            row.append(level_renderable)

        if show_arrow:
            table.add_column(width=3, style=level_style, justify="left")
            row.append(Text("→"))

        # Message
        table.add_column(overflow="fold", justify="left", width=message_width, style=message_style)
        row.append(self._render_message(renderables))

         #should treat options as one block so they can multline when needed.
        option_colomn = []
        option_width = 0
        if path_renderable is not None:
            path_renderable = self._render_path(path, line_no, link_path, path_width) # rebuild it since we can fold now
            option_colomn.append(path_renderable)
            option_width += path_width

        if function_renderable is not None:
            option_colomn.append(function_renderable)
            option_width += function_width
        table.add_column(
                style=self._PATH_STYLE, justify="right", width=path_width, overflow="fold"
            )  # Path column
        row.append(Renderables(option_colomn))
        table.add_row(*row)
        return table

    def _assign_variable_widths(
        self,
        console: Console,
        time_renderable: Text | None,
        level_renderable: Text | None,
        path_renderable: Text | None,
        function_renderable: Text | None,
    ) -> tuple[int, int | None, int | None, bool]:
        """
        Compute column widths using a priority-based budget allocation strategy.

        Strategy:
            1. Start with the total terminal width.
            2. Subtract invariant columns:
               - time (dynamic, but already rendered)
               - level (fixed width)
               - arrow (fixed width)
            3. Reserve space for the message column:
               - message is guaranteed `min_message_width` if possible
               - message always wins conflicts
            4. Allocate remaining width to optional metadata columns:
               - path (up to `max_path_width`)
               - function (up to `max_function_width`)
            5. If space is insufficient (space < min_message_width):
               - optional columns collapse to zero before message is reduced
               - The arrow column is removed and its width is reclaimed for the message.

            6. If terminal width is unknown:
               - fall back to user-controlled minimums

        Important properties:
            - Widths are computed once per row, before rendering.
            - No Rich auto-sizing or reflow is relied upon.
            - Zero-width columns are intentional and indicate full collapse.

        Args:
            console:
                Active Rich Console used to determine terminal width.
            time_renderable:
                Rendered timestamp, if enabled.
            level_renderable:
                Rendered level text, if enabled.
            path_renderable:
                Rendered path text, if enabled.
            function_renderable:
                Rendered function text, if enabled.

        Returns:
            A tuple of:
                (message_width, path_width, function_width, show_arrow)

            Where:
                - message_width is always non-negative
                - path_width / function_width may be zero to indicate full collapse
                - show_arrow indicates whether the arrow column should be rendered
        """

        path_width: int | None = None
        function_width: int | None = None

        # Space Reservations
        show_arrow: bool = False
        arrow_width: int = 0
        right_gutter = 0

        # Determine available horizontal space from the console
        console_width = console.width

        # 120 console width for optional injections
        if console_width is not None and console_width >= 120:
            right_gutter = self._right_gutter
            arrow_width = 3
            show_arrow = True

        available_width = console_width - right_gutter
        # Fallback: unknown terminal width → user-controlled minimums
        if available_width is None or not isinstance(available_width, int):
            return (
                self.min_message_width,
                self._minimal_col_width,
                self._minimal_col_width,
                show_arrow,
            )


        assert isinstance(available_width, int)

        # ── Subtract invariant columns

        # Time column: dynamic width, already rendered
        if time_renderable is not None:
            if self._last_time is not None:
                available_width -= max(
                    self._last_time.cell_len,
                    time_renderable.cell_len,
                )
            else:
                available_width -= time_renderable.cell_len

        # Level column: fixed width
        if level_renderable is not None:
            available_width -= self.level_width

        # Arrow column: provisionally reserved (may be reclaimed later)
        available_width -= arrow_width

        # ── Compute optional metadata budget

        # Maximum width required by optional columns if fully expanded
        option_width: int = 0
        if path_renderable is not None:
            option_width += self.max_path_width
        if function_renderable is not None:
            option_width += self.max_function_width
        # ── Width allocation strategy

        # Case 1: Not enough space for options + minimum message width
        if available_width < (option_width + self.min_message_width):
            # Case 1a: Even minimum message width cannot be satisfied
            if available_width < self.min_message_width:
                # Reclaim arrow width to preserve message readability
                message_width = available_width + arrow_width + self._right_gutter
                show_arrow = False

                # Optional metadata collapses completely
                if path_renderable is not None:
                    path_width = 0
                if function_renderable is not None:
                    function_width = 0

                self._layout_degradation_flag = True

            # Case 1b: Message can be satisfied, options must shrink proportionally
            else:
                available_width -= self.min_message_width
                message_width = self.min_message_width

                if path_renderable is not None:
                    path_width = max(
                        0,
                        math.floor(available_width * self.max_path_width / option_width),
                    )
                    if path_width < self._minimal_col_width:
                        message_width += path_width
                        path_width = 0
                        self._layout_degradation_flag = True

                if function_renderable is not None:
                    function_width = max(
                        0,
                        math.floor(available_width * self.max_function_width / option_width),
                    )
                    if function_width < self._minimal_col_width:
                        message_width += function_width
                        function_width = 0
                        self._layout_degradation_flag = True


        # Case 2: Sufficient space for all columns
        else:
            if path_renderable is not None:
                path_width = min(
                    self.max_path_width,
                    path_renderable.cell_len,
                )
                available_width -= path_width

            if function_renderable is not None:
                function_width = min(
                    self.max_function_width,
                    function_renderable.cell_len,
                )
                available_width -= function_width

            # Message absorbs remaining width
            message_width = available_width
        return message_width, path_width, function_width, show_arrow

    def _render_message(self, renderables: Iterable[ConsoleRenderable]) -> Renderables:
        guided_renderables = []
        for renderable in renderables:
            if hasattr(renderable, 'with_indent_guides'):
                renderable = renderable.with_indent_guides(style=self._INDENT_STYLE)
            guided_renderables.append(renderable)
        return Renderables(guided_renderables)

    def _render_function_(self, function_name: str | None, path_renderable: Text | None) -> Text:
        if not function_name:
            return Text()

        function_name = function_name.strip()
        if not function_name:
            return Text()

        # Truncate function name to fit in column (accounting for " | " prefix and " " suffix)
        function_text = Text(style=self._FUNCTION_STYLE)
        if path_renderable is not None:
            function_text.append(" ")
        function_text.append("[")
        function_text.append(function_name)
        function_text.append("]")
        return function_text

    def _render_time(
        self,
        console: Console,
        log_time: datetime | None,
        time_format: str | FormatTimeCallable | None,
    ) -> Text:
        log_time = log_time or console.get_datetime()
        fmt = time_format or self.time_format

        if callable(fmt):
            time_text = fmt(log_time)
        else:
            time_text = Text(log_time.strftime(fmt) + " ")

        if self.omit_repeated_times and time_text == self._last_time:
            display = Text()
        else:
            display = time_text
        self._last_time = time_text.copy()
        display.style = self._TIME_STYLE
        return display

    def _render_path(
        self,
        path: Path,
        line_no: int | None,
        link_path: str | None,
        path_width: int = 10,
    ) -> Text:
        text = Text(style=self._PATH_STYLE)

        parts = path.parts
        running_len = 0

        # render parent parts
        for part in parts[:-1]:
            part_len = len(part) + 1  # +1 for "/"
            if running_len + part_len > path_width:
                text.append("\n")
                running_len = 0

            text.append(part)
            text.append("/")
            running_len += part_len

        # render filename (linkable)
        filename = parts[-1]
        filename_style = f"link {link_path}" if link_path else ""
        text.append(filename, style=filename_style)

        # render line number
        if line_no is not None:
            text.append(":")
            line_style = f"link {link_path}#{line_no}" if link_path else ""
            text.append(str(line_no), style=line_style)

        return text

    def _get_level_style(self, key: TextType, message: bool = False) -> Style:
        name = str(key).strip()
        if message:
            name = f"MESSAGE_{name}"

        return self._LEVEL_STYLES.get(name, Style.null())

    @staticmethod
    def add_divider(
        table: Table, row: list[RenderableType], level_style: Style
    ) -> tuple[Table, list[RenderableType]]:
        table.add_column(width=1, justify="center")
        row.append(Text("-", style=level_style))
        return table, row

    @property
    def is_layout_degraded(self) -> bool:
        return self._layout_degradation_flag
