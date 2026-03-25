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
from ..._Internal.State.Env import get_console_width


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
    Budget-based column layout renderer for Rich log output.

    Called once per log record from ``SparkRichHandler.render()``. Computes
    column widths against the current terminal width before rendering, so no
    Rich auto-sizing or reflow occurs at display time.

    Layout priority (left to right):
        1. Time — allocated first, collapses inline with level under pressure
        2. Level — fixed width
        3. Arrow separator — shown only when terminal width exceeds 120 columns
        4. Message — guaranteed ``min_message_width``; highest priority
        5. Path — optional, right-aligned, first to collapse
        6. Function — optional, right-aligned, collapses after path

    Optional metadata columns are dropped to zero width before the message
    column is compressed. The degradation gate tracks which columns were
    hidden and prevents redundant per-record recalculation.
    """

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
        """Initialize with layout settings and reset all per-instance mutable state."""
        super().__init__()
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

        self._degradation_gate: _DegradationGates = _DegradationGates.NONE
        self._layout_degradation_flag: bool = False
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
        Render one log record as a Rich ``Table`` row with explicit, pre-computed column widths.

        All column widths are resolved against the current terminal width before
        the table is constructed. ``expand=False`` is enforced so Rich never
        reflowing or auto-sizes any column at display time.

        Column order: time → level → arrow → message → path → function.
        Optional metadata columns collapse to zero width before the message
        column is reduced. The arrow separator is omitted on narrow terminals
        (below 120 columns).
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
        """Build styled Text renderables for each active column based on current display settings."""
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
        """Add time and level columns to the table; collapses time inline with level when time_width is zero."""
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
        """Add path and function as a single combined right-aligned option column when either has non-zero width."""
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
        """Compute (message_width, time_width, path_width, function_width) via priority-based budget allocation."""

        console_width = console.width
        if console_width is None or not isinstance(console_width, int):
            raise TypeError(
                f"Console width must be an int, got {console_width!r} "
                f"({type(console_width).__name__})"
            )

        # When Rich is using its default fallback width (console._width is None, meaning no
        # explicit width was set and os.get_terminal_size() failed), attempt a deeper probe via
        # platform-native APIs that succeed even when stdout is redirected.
        # If the native probe also fails, console_width stays at Rich's 80-column default and
        # the degradation warning will fire normally when columns cannot fit.
        if getattr(console, "_width", None) is None:
            native_width = get_console_width()
            if native_width is not None:
                console_width = native_width
            else:
                console_width = console.width  # explicit: keep Rich's 80-col fallback

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
        """Return (allocated_width, remaining_width, degraded); degraded is True when the column was collapsed to zero."""
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
        """Wrap renderables in indent guides if configured and the renderable supports them."""
        guided_renderables = []
        for renderable in renderables:
            if self.indent_guide and isinstance(renderable, _SupportsIndentGuides):
                renderable = renderable.with_indent_guides(style=self._INDENT_STYLE)
            guided_renderables.append(renderable)
        return Renderables(guided_renderables)

    def _format_function_name(
        self, function_name: str | None, path_renderable: Text | None
    ) -> Text:
        """Format function name as ``[name]`` with a leading space when a path renderable is present."""
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
        """Format the record timestamp; returns an empty Text when omit_repeated_times suppresses a duplicate."""
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
        """Render path segments and line number as a styled, optionally linked Rich Text."""

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
        """Look up the Rich Style for a given level name; when message=True returns the message-body style."""
        name = str(key).strip()
        if message:
            name = f"MESSAGE_{name}"

        return self._LEVEL_STYLES.get(name, Style.null())

    @property
    def is_layout_degraded(self) -> bool:
        """True when at least one optional column was collapsed due to insufficient terminal width."""
        return self._layout_degradation_flag

    def degraded_columns(self) -> list[str]:
        """Return the names of optional columns that were hidden during the last layout allocation."""
        hidden: list[str] = []
        if self.show_path and self._degradation_gate in (
            _DegradationGates.TIME,
            _DegradationGates.PATH,
        ):
            hidden.append("Path")
        if self.show_function and self._degradation_gate in (
            _DegradationGates.TIME,
            _DegradationGates.PATH,
            _DegradationGates.FUNCTION,
        ):
            hidden.append("Function")
        return hidden

    @staticmethod
    def _console_has_space(console: Console) -> bool:
        """Return True when the console width is known and at least 120 columns."""
        if console is None:
            return False
        if console.width is None:
            return False
        if console.width < 120:
            return False
        return True

    @staticmethod
    def _get_minimal_path_split(path: Text) -> int:
        """Return the length of the longest path segment, used as the minimum viable path column width."""
        return max([len(p) for p in Path(path.plain).as_posix().split("/")])
