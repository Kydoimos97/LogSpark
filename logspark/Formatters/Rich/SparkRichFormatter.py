from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from rich._log_render import FormatTimeCallable
from rich.console import Console, ConsoleRenderable, RenderableType
from rich.containers import Renderables
from rich.style import Style
from rich.table import Table
from rich.text import Text, TextType

from ..._Internal import _DegradationGates


@runtime_checkable
class _SupportsIndentGuides(Protocol):
    """Protocol for objects that support indent guides"""

    def with_indent_guides(
        self,
        indent_size: int | None = None,
        *,
        character: str = "│",
        style: "str | Style" = "dim green",
    ) -> "Text": ...


# noinspection PyUnusedFunction
@runtime_checkable
class _HasPlain(Protocol):
    """Protocol for objects that support plain text"""

    @property
    def plain(self) -> str: ...


@dataclass
class PathInfo:
    path: Path
    uri: str | None
    lineno: int | None


class SparkRichFormatter:
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

    _degradation_gate: _DegradationGates = _DegradationGates.NONE
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
        max_path_width: int = 20,
        max_function_width: int = 25,
        min_message_width: int = 40,
        indent_guide: str | None = "│",
    ) -> None:
        self.show_time = show_time
        self.show_level = show_level
        self.show_path = show_path
        self.show_function = show_function

        self.indent_guide = indent_guide

        self.time_format = time_format
        self.omit_repeated_times = omit_repeated_times

        self.level_width = level_width
        self.max_path_width = max_path_width
        self.max_function_width = max_function_width
        self.min_message_width = min_message_width

        self._last_time: Text | None = None
        self._minimal_col_width: int = 10
        self._minimal_path_width: int = 0
        self._gutter_width: int = 4
        self._arrow_width: int = 3
        self._padding: int = 1

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
        if not self._console_has_space(console):
            self._gutter_width = 0

        path_info: PathInfo | None = None
        if path is not None:
            path_info = PathInfo(path, link_path, line_no)

        table = Table.grid(padding=(0, self._padding), expand=False)
        message_style = self._get_level_style(level, message=True)
        row: list[RenderableType] = []

        # Create Renderables
        time_renderable, level_renderable, path_renderable, function_renderable, level_style = (
            self._create_renderables(
                console=console,
                log_time=log_time,
                time_format=time_format,
                level=level,
                path_info=path_info,
                function_name=function_name,
            )
        )

        if path_renderable is None:
            path_info = None

        # Set the Variable Widths
        message_width, time_width, path_width, function_width = self._assign_variable_widths(
            console=console,
            time_renderable=time_renderable,
            level_renderable=level_renderable,
            path_renderable=path_renderable,
            function_renderable=function_renderable,
        )
        # Create Table
        table, row = self._handle_invariant_columns(
            table=table,
            row=row,
            time_renderable=time_renderable,
            level_renderable=level_renderable,
            time_width=time_width,
            level_style=level_style,
        )

        if self._console_has_space(console):
            table.add_column(width=self._arrow_width, style=level_style, justify="left")
            row.append(Text("→"))

        # Message
        table.add_column(overflow="fold", justify="left", width=message_width, style=message_style)
        row.append(self._format_renderables(renderables))

        # should treat options as one block so they can multline when needed.
        table, row = self._handle_option_columns(
            table=table,
            row=row,
            path_info=path_info,
            function_renderable=function_renderable,
            path_width=path_width,
            function_width=function_width,
        )

        # Gutter
        if self._gutter_width > 0:
            table.add_column(width=self._gutter_width, style=Style.null())

        table.add_row(*row)
        return table

    def _create_renderables(
        self,
        console: Console,
        log_time: datetime | None,
        time_format: str | FormatTimeCallable | None,
        level: TextType,
        path_info: PathInfo | None,
        function_name: str | None,
    ) -> tuple[Text | None, Text | None, Text | None, Text | None, Style]:
        level_style = self._get_level_style(level)
        if self.show_time:
            time_renderable = self._format_time(console, log_time, time_format)
        else:
            time_renderable = None
        if self.show_level:
            level_display = (
                level.plain.strip() if isinstance(level, _HasPlain) else str(level).strip()
            )
            level_renderable = Text(level_display, style=level_style)
        else:
            level_renderable = None
        if self.show_path and path_info:
            path_renderable = self._format_path(path_info.path, path_info.lineno, path_info.uri)
        else:
            path_renderable = None

        if self.show_function and function_name:
            function_renderable = self._format_function_name(function_name, path_renderable)
        else:
            function_renderable = None
        return time_renderable, level_renderable, path_renderable, function_renderable, level_style

    def _handle_invariant_columns(
        self,
        table: Table,
        row: list[RenderableType],
        time_renderable: Text | None,
        level_renderable: Text | None,
        time_width: int,
        level_style: Style,
    ) -> tuple[Table, list[RenderableType]]:
        if time_renderable is not None:
            if time_width > 0:
                table.add_column(style=self._TIME_STYLE, width=time_width, justify="left")
                row.append(time_renderable)

        if level_renderable is not None:
            table.add_column(width=self.level_width, style=level_style, justify="left")
            if time_width == 0 and time_renderable is not None:
                row.append(Renderables([level_renderable, time_renderable]))
            else:
                row.append(level_renderable)
        return table, row

    def _handle_option_columns(
        self,
        table: Table,
        row: list[RenderableType],
        path_info: PathInfo | None,
        function_renderable: Text | None,
        path_width: int,
        function_width: int,
    ) -> tuple[Table, list[RenderableType]]:
        option_colomn = []
        option_width = 0
        if path_info is not None and path_width > 0:
            path_renderable = self._format_path(
                path_info.path, path_info.lineno, path_info.uri, path_width
            )  # rebuild it since we can fold now
            option_colomn.append(path_renderable)
            option_width += path_width

        if function_renderable is not None and function_width > 0:
            option_colomn.append(function_renderable)
            option_width += function_width

        if option_width > 0:
            table.add_column(
                style=self._PATH_STYLE, justify="right", width=option_width, overflow="fold"
            )

        row.append(Renderables(option_colomn))
        return table, row

    def _assign_variable_widths(
        self,
        console: Console,
        time_renderable: Text | None,
        level_renderable: Text | None,
        path_renderable: Text | None,
        function_renderable: Text | None,
    ) -> tuple[int, int, int, int]:
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
                (message_width, time_width, path_width, function_width)

            Where:
                - message_width is always non-negative
                - path_width / function_width may be zero to indicate full collapse
                - show_arrow indicates whether the arrow column should be rendered
        """

        console_width = console.width
        if console_width is None or not isinstance(console_width, int):
            raise TypeError(
                f"Console width must be an int, got {console_width!r} "
                f"({type(console_width).__name__})"
            )

        available_width = console_width - self._gutter_width - self._padding

        raw_time_width = 0
        if time_renderable is not None:
            raw_time_width = (
                max(self._last_time.cell_len, time_renderable.cell_len)
                if self._last_time is not None
                else time_renderable.cell_len
            )

        raw_level_width = 0
        if level_renderable is not None:
            raw_level_width = self.level_width

        # Invariant collapses to its largest format
        invariant_width = max(raw_level_width, raw_time_width)
        invariant_diff = max(raw_time_width - raw_level_width, 0)

        # Message is tested given one column for invariants
        available_width -= invariant_width

        # arrow is environmental
        has_space = self._console_has_space(console)
        if has_space:
            available_width -= self._arrow_width

        if self._layout_degradation_flag and self._degradation_gate == _DegradationGates.TIME:
            # No time means no options
            return available_width, 0, 0, 0

        # 2. time
        time_width = 0
        if time_renderable is not None:
            time_width, available_width, degraded = self._allocate_or_degrade(
                has_space=has_space,
                available_width=available_width,
                desired_width=raw_time_width,
                minimal_width=raw_time_width,  # full-or-inline rule
                renderable=time_renderable,
            )

            if degraded and not self._layout_degradation_flag:
                self._degradation_gate = _DegradationGates.TIME
                self._layout_degradation_flag = True
                return available_width, 0, 0, 0
            else:
                # if time get allocated make sure the diff is reassigned
                available_width += invariant_diff

        if self._layout_degradation_flag and self._degradation_gate == _DegradationGates.PATH:
            # No time means no options
            return available_width, time_width, 0, 0

        # 3. path
        path_width = 0
        if path_renderable is not None:
            min_path_width = self._get_minimal_path_split(path_renderable)
            if has_space:
                min_path_width = max(path_width, self._minimal_path_width)
                self._minimal_path_width = min_path_width
        else:
            min_path_width = 0

        path_width, available_width, degraded = self._allocate_or_degrade(
            has_space=has_space,
            available_width=available_width,
            desired_width=(
                min(self.max_path_width, path_renderable.cell_len)
                if path_renderable is not None
                else 0
            ),
            minimal_width=min_path_width,
            renderable=path_renderable,
        )

        if degraded and not self._layout_degradation_flag:
            self._degradation_gate = _DegradationGates.PATH
            self._layout_degradation_flag = True
            return available_width, time_width, 0, 0

        if self._layout_degradation_flag and self._degradation_gate == _DegradationGates.FUNCTION:
            # No path means no function
            return available_width, time_width, path_width, 0

        function_width, available_width, degraded = self._allocate_or_degrade(
            has_space=has_space,
            available_width=available_width,
            desired_width=(
                min(self.max_function_width, function_renderable.cell_len)
                if function_renderable is not None
                else 0
            ),
            minimal_width=self._minimal_col_width,
            renderable=function_renderable,
        )

        if degraded and not self._layout_degradation_flag:
            self._degradation_gate = _DegradationGates.FUNCTION
            self._layout_degradation_flag = True
            return available_width, time_width, path_width, 0

        return available_width, time_width, path_width, function_width

    def _allocate_or_degrade(
        self,
        *,
        has_space: bool,
        available_width: int,
        desired_width: int,
        minimal_width: int | None = None,
        renderable: RenderableType | None,
    ) -> tuple[int, int, bool]:
        """
        Try to allocate width for a column.
        If allocation is not viable, trigger degradation and return 0 width.

        Returns:
            (allocated_width, remaining_width)
        """
        if minimal_width is None:
            minimal_width = self._minimal_col_width

        # we shrink if we have no space else we expand
        if desired_width < minimal_width:
            if has_space:
                desired_width = minimal_width
            else:
                minimal_width = desired_width

        if renderable is None:
            return 0, available_width, False

        max_width = available_width - self.min_message_width - self._padding
        if max_width < minimal_width:
            return 0, available_width, True

        if max_width < desired_width:
            return minimal_width, available_width - minimal_width - self._padding, False

        return desired_width, available_width - desired_width - self._padding, False

    def _format_renderables(self, renderables: Iterable[ConsoleRenderable]) -> Renderables:
        guided_renderables = []
        for renderable in renderables:
            if self.indent_guide and isinstance(renderable, _SupportsIndentGuides):
                renderable = renderable.with_indent_guides(style=self._INDENT_STYLE)
            guided_renderables.append(renderable)
        return Renderables(guided_renderables)

    def _format_function_name(
        self, function_name: str | None, path_renderable: Text | None
    ) -> Text:
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

    def _format_time(
        self,
        console: Console,
        log_time: datetime | None,
        time_format: str | FormatTimeCallable | None,
    ) -> Text | None:
        log_time = log_time or console.get_datetime()
        fmt = time_format or self.time_format

        if callable(fmt):
            time_text = fmt(log_time)  # type: ignore[call-arg]
        else:
            time_text = Text(log_time.strftime(fmt) + " ")

        display = time_text
        if not self._degradation_gate == _DegradationGates.TIME:
            if self.omit_repeated_times and time_text == self._last_time:
                display = Text()

        self._last_time = time_text.copy()
        display.style = self._TIME_STYLE
        return display

    def _format_path(
        self,
        path: Path,
        line_no: int | None,
        link_path: str | None,
        path_width: int = 10,
    ) -> Text:

        if isinstance(path, str):
            path = Path(path)

        text = Text(style=self._PATH_STYLE)

        parts = path.as_posix().split("/")
        if len(parts) == 0:
            return text

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
        if len(parts) > 1 and running_len + len(filename) + 1 > path_width:
            text.append("\n")
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

    @property
    def is_layout_degraded(self) -> bool:
        return self._layout_degradation_flag

    @staticmethod
    def _console_has_space(console: Console) -> bool:
        if console is None:
            return False
        if console.width is None:
            return False
        if console.width < 120:
            return False
        return True

    @staticmethod
    def _get_minimal_path_split(path: Text) -> int:
        return max([len(p) for p in Path(path.plain).as_posix().split("/")])
