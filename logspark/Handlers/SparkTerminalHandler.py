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
    Human-readable terminal logging handler with optional Rich rendering.

    This handler targets interactive, developer-facing output. When Rich is
    available, it delegates rendering to a Rich-based handler for structured
    layout, colors, and enhanced tracebacks. When Rich is not available, it
    falls back to a standard ``logging.StreamHandler``.

    The handler is implemented as a *composed handler*: it wraps an internal
    handler instance and forwards log records after applying LogSpark-specific
    policies such as traceback formatting.

    Features:
        - Optional Rich-enhanced terminal output
        - Graceful fallback to stdlib StreamHandler when Rich is unavailable
        - Configurable display of time, level, path, and function name
        - Traceback rendering controlled via ``TracebackOptions``
        - Automatic terminal size detection with conservative defaults

    Traceback handling:
        The handler inspects the ``traceback_policy`` attribute on log records.
        Depending on the policy, exception information may be suppressed,
        compacted, or fully rendered by Rich.

    Console configuration:
        A pre-is_configured Rich ``Console`` may be supplied directly. When a
        console is provided, the ``stream`` argument must not be set.

    Intended use:
        This handler is designed for human-readable output during development
        and interactive use. It is not intended for high-volume or structured
        logging pipelines.
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
        level_width: int = 8,
        log_time_format: "str | FormatTimeCallable | None" = "%H:%M:%S",
    ) -> None:
        """
        Initialize a terminal logging handler.
        """

        # Rich not available - fall back to stdlib StreamHandler
        std_lib_time_format = validate_stdlib_timeformat(log_time_format)
        spark_stream = resolve_stream(stream)

        fmt: logging.Formatter | None = None
        fmt_string = generate_stdlib_format(
            show_time=show_time,
            show_level=show_level,
            level_width=level_width,
            show_path=show_path,
            show_function=show_function,
        )
        _compatible = is_color_compatible_terminal(spark_stream)
        if use_color:
            # Don't pass the console as we aren't checking rich
            if _compatible:
                from ..Formatters import SparkColorFormatter

                fmt = SparkColorFormatter(
                    fmt=fmt_string,
                    datefmt=std_lib_time_format,
                    tb_policy=traceback_policy,
                    multiline=multiline
                )
            else:
                emit_color_incompatible_console_warning()

        if fmt is None:
            from ..Formatters.SparkBaseFormatter import SparkBaseFormatter
            fmt = SparkBaseFormatter(
                fmt=fmt_string,
                datefmt=std_lib_time_format,
                traceback_policy=traceback_policy,
                multiline=multiline
            )

        super().__init__(stream=spark_stream)
        self.setFormatter(fmt)
        self.setLevel(level)
