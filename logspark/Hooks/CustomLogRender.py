from collections.abc import Iterable
from datetime import datetime

from rich._log_render import FormatTimeCallable
from rich.console import Console, ConsoleRenderable, RenderableType
from rich.containers import Renderables
from rich.style import Style
from rich.table import Table
from rich.text import Text, TextType


class CustomLogRender:
    _TIME_STYLE = Style(color="white", dim=True)
    _PATH_STYLE = Style(color="cyan")
    _FUNCTION_STYLE = Style(color="white", dim=True)
    _LEVEL_STYLES = {
        "DEBUG": Style(color="cyan", dim=True),
        "INFO": Style(color="green"),
        "WARNING": Style(color="yellow"),
        "ERROR": Style(color="red"),
        "CRITICAL": Style(color="magenta", bold=True),
        "MESSAGE_DEBUG": Style(color="white", dim=True, italic=True),
        "MESSAGE_INFO": Style(color="white"),
        "MESSAGE_WARNING": Style.null(),
        "MESSAGE_ERROR": Style.null(),
        "MESSAGE_CRITICAL": Style.null(),
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
        level_width: int | None = 8,
    ) -> None:
        self.show_time = show_time
        self.show_level = show_level
        self.show_path = show_path
        self.show_function = show_function
        self.time_format = time_format
        self.omit_repeated_times = omit_repeated_times
        self.level_width = level_width
        self._last_time: Text | None = None

    def __call__(
        self,
        console: Console,
        renderables: Iterable[ConsoleRenderable],
        *,
        log_time: datetime | None = None,
        time_format: str | FormatTimeCallable | None = None,
        level: TextType = "",
        path: str | None = None,
        line_no: int | None = None,
        link_path: str | None = None,
        function_name: str | None = None,
    ) -> Table:
        table = Table.grid(padding=(0, 0), expand=True)
        level_style = self._get_level_style(level)
        message_style = self._get_level_style(level, message=True)
        row: list[RenderableType] = []

        if self.show_time:
            table.add_column(style=self._TIME_STYLE, width=10, justify="right")
            renderable = self._render_time(console, log_time, time_format)
            row.append(renderable)
            table.add_column(width=1, style=level_style)
            row.append(Text(" "))
        if self.show_level:
            table.add_column(width=self.level_width, style=level_style)
            level_display = str(level).strip() if hasattr(level, "plain") else str(level).strip()
            renderable = Text(level_display, style=level_style)
            row.append(renderable)
            if self.show_path and path or self.show_function:
                table, row = self.add_divider(table, row, level_style)

        if self.show_path and path:
            table.add_column(no_wrap=True, style=self._PATH_STYLE)  # Path column
            renderable = self._render_path(path, line_no, link_path)
            row.append(renderable)
            if self.show_function:
                table, row = self.add_divider(table, row, level_style)

        if self.show_function:
            table.add_column(style=self._FUNCTION_STYLE)
            renderable = self._render_function_(function_name)
            row.append(renderable)

        # Arrow
        table.add_column(width=2, style=level_style)
        row.append(Text("→"))

        # Message
        table.add_column(style=message_style, overflow="fold")
        row.append(Renderables(renderables))

        table.add_row(*row)
        return table

    def _render_function_(self, function_name: str | None) -> Text:
        if not function_name:
            return Text()

        function_name = function_name.strip()
        if not function_name:
            return Text()

        # Truncate function name to fit in column (accounting for " | " prefix and " " suffix)
        function_text = Text(style=self._FUNCTION_STYLE)
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
            time_text = Text(log_time.strftime(fmt))

        if self.omit_repeated_times and time_text == self._last_time:
            display = Text(" " * (len(time_text) + 3))
        else:
            display = time_text
        self._last_time = time_text.copy()
        display.style = self._TIME_STYLE
        return display

    def _render_path(
        self,
        path: str,
        line_no: int | None,
        link_path: str | None,
    ) -> Text:
        text = Text(style=self._PATH_STYLE)
        text.append(path, style=f"link {link_path}" if link_path else "")

        if line_no:
            text.append(":")
            text.append(
                str(line_no),
                style=f"link {link_path}#{line_no}" if link_path else "",
            )
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
