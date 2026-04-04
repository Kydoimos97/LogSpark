from enum import Enum


class _DegradationGates(str, Enum):
    TIME = "time"
    PATH = "path"
    FUNCTION = "function"
    NONE = None
