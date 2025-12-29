from enum import Enum


class TracebackOptions(Enum):
    """Traceback inclusion policies for log output"""

    NONE = None
    COMPACT = "compact"
    FULL = "full"


class PresetOptions(str, Enum):
    TERMINAL = "terminal"
    JSON = "json"
