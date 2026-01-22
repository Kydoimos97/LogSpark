from dataclasses import dataclass
from enum import Enum


class PresetOptions(str, Enum):
    TERMINAL = "terminal"
    JSON = "json"


@dataclass
class SparkRichHandlerSettings:
    omit_repeated_times: bool = True
    enable_link_path: bool = True
    min_message_width: int = 40
    max_path_width: int = 40
    max_function_width: int = 25
    tracebacks_width: int | None = None
    tracebacks_extra_lines: int = 3
    indent_guide: str | None = "|"


class TracebackOptions(Enum):
    """Traceback inclusion policies for log output"""

    HIDE = "hide"
    COMPACT = "compact"
    FULL = "full"


class PathResolutionSetting(Enum):
    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    FILE = "file"
