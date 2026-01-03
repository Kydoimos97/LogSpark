import os
import shutil
from importlib.util import find_spec
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console


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


def has_viable_output_surface(console: "Console | None" = None) -> bool:
    """If height and size aren't available or set the console is generally not supported by rich"""

    # rich validator
    if console is not None and hasattr(console, "is_terminal"):
        if not console.is_terminal:
            return False

    # no output surface
    _w, _h = shutil.get_terminal_size((0, 0))
    if _w == 0 and _h == 0:
        return False

    # Force Color Override: # https://force-color.org/
    if os.environ.get("FORCE_COLOR", "").lower() != "":
        # Rich already does this but explicitly rechecking for referencing purposes
        return True

    # Return True since all applicable checks passed
    return True


def is_rich_available() -> bool:
    try:
        return find_spec("rich") is not None
    except ValueError:
        # Module present but broken / partially initialized
        return False
