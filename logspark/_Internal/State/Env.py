import os
from importlib.util import find_spec
from pathlib import Path


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


def resolve_project_root() -> Path | None:
    if root := os.environ.get("PROJECT_ROOT"):
        return Path(root)

    if venv := os.environ.get("VIRTUAL_ENV"):
        return Path(venv).parent

    cur = Path.cwd().resolve()
    for parent in (cur, *cur.parents):
        if (parent / "pyproject.toml").exists():
            return parent

    return None