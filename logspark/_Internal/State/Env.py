import os
from importlib.util import find_spec


def is_silenced_mode() -> bool:
    """
    When LOGSPARK_MODE=silenced, all logging pipelines remain fully active,
    but output is discarded. This mode is intended for tests and high-volume
    scenarios where logging correctness must be validated without producing output.
    """
    return os.getenv("LOGSPARK_MODE", "").lower() == "silenced"


def is_fast_mode() -> bool:
    """
    Performance optimization that trades call-site accuracy for speed.
    When set, uses constant-time stacklevel resolution instead of frame walking.
    Recommended for high-throughput scenarios where logging performance is critical.
    """
    return os.getenv("LOGSPARK_MODE", "").lower() == "fast"


def is_rich_available() -> bool:
    """
    Check if Rich library is available for import.
    """
    try:
        return find_spec("rich") is not None
    except ValueError:
        # Module present but broken / partially initialized
        return False
