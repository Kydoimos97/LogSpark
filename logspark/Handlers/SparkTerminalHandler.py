import logging
from typing import TYPE_CHECKING

from .._Internal.Func import (
    emit_color_incompatible_console_warning,
    generate_stdlib_format,
    is_color_compatible_terminal,
    resolve_stream,
    validate_stdlib_timeformat,
)
from ..Types.Protocol import SupportsWrite

if TYPE_CHECKING:
    from rich._log_render import FormatTimeCallable

    from ..Types.Options import TracebackOptions


class SparkTerminalHandler(logging.StreamHandler[SupportsWrite]):
    """
    Human-readable terminal logging handler for developer-facing output.

    Extends ``logging.StreamHandler`` directly — no composition or delegation.
    Selects a formatter at construction time based on terminal color capability:
    ``SparkColorFormatter`` when the stream supports ANSI color, otherwise
    ``SparkBaseFormatter`` with a one-time color-incompatibility warning.

    Traceback rendering is delegated to the formatter via ``traceback_policy``.
    When ``multiline=False``, exception text is collapsed to a single line.
    """

    def __init__(
        self,
        level: int | str = logging.NOTSET,
        stream: SupportsWrite | None = None,
        *,
        use_color: bool = True,
        show_time: bool = True,
        show_level: bool = True,
        show_path: bool = True,
        show_function: bool = False,
        traceback_policy: "TracebackOptions | None" = None,
        multiline: bool = True,
        level_width: int = 9,
        log_time_format: "str | FormatTimeCallable | None" = "%H:%M:%S",
        link_path: bool = False,
    ) -> None:
        """Initialize formatter selection and underlying StreamHandler."""

        std_lib_time_format = validate_stdlib_timeformat(log_time_format)
        spark_stream = resolve_stream(stream)

        fmt: logging.Formatter | None = None
        _compatible = is_color_compatible_terminal(spark_stream)
        if use_color:
            if _compatible:
                from ..Formatters import SparkColorFormatter

                fmt = SparkColorFormatter(
                    datefmt=std_lib_time_format,
                    show_time=show_time,
                    show_level=show_level,
                    show_path=show_path,
                    show_function=show_function,
                    level_width=level_width,
                    link_path=link_path,
                    tb_policy=traceback_policy,
                    multiline=multiline,
                )
            else:
                emit_color_incompatible_console_warning()

        if fmt is None:
            from ..Formatters.SparkBaseFormatter import SparkBaseFormatter
            fmt_string = generate_stdlib_format(
                show_time=show_time,
                show_level=show_level,
                level_width=level_width,
                show_path=show_path,
                show_function=show_function,
            )
            fmt = SparkBaseFormatter(
                fmt=fmt_string,
                datefmt=std_lib_time_format,
                tb_policy=traceback_policy,
                multiline=multiline,
            )

        super().__init__(stream=spark_stream)
        self.setFormatter(fmt)
        self.setLevel(level)
