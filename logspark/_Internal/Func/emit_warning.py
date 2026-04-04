import warnings

from .colorize import colorize_yellow
from .is_color_compatible_terminal import is_color_compatible_terminal


def emit_warning(message: str, category: type[Warning] | None = None, stacklevel: int = 2) -> None:
    if is_color_compatible_terminal():
        message = colorize_yellow(message)

    stacklevel += 1

    warnings.warn(
        message=message,
        category=category,
        stacklevel=stacklevel,
    )
