from dataclasses import dataclass
from enum import Enum

from typing_extensions import TypeVar

E = TypeVar("E", bound=Enum)

class PresetOptions(str, Enum):
    """Named presets for quick handler selection in ``configure()``."""

    TERMINAL = "terminal"
    JSON = "json"


@dataclass
class SparkRichHandlerSettings:
    """
    Advanced layout and rendering settings for ``SparkRichHandler``.

    Passed as the ``settings=`` argument to ``SparkRichHandler``. All fields
    have sensible defaults and can be overridden individually.
    """

    omit_repeated_times: bool = True
    enable_link_path: bool = True
    min_message_width: int = 40
    max_path_width: int = 40
    max_function_width: int = 25
    tracebacks_width: int | None = None
    tracebacks_extra_lines: int = 3
    indent_guide: str | None = "|"


class TracebackOptions(Enum):
    """Traceback inclusion policies for log output."""

    HIDE = "hide"
    COMPACT = "compact"
    FULL = "full"


class PathResolutionSetting(Enum):
    """Controls how source file paths are resolved and displayed in log output."""

    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    FILE = "file"

def safe_coerce_enum(value: str, enum: type[E], default: E) -> E:
    """Coerce a string to the given Enum, returning default when the value is not a valid member."""
    try:
        val = enum(value)
        return val
    except ValueError:
        return default

