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
    """Resolve the project root directory using explicit configuration first,
    then environment context, and finally filesystem heuristics.

    Priority order:
    1) Explicit PROJECT_ROOT env override
    2) Active virtual environment location
    3) Upward search from CWD for common project markers

    Returns None if no reasonable root can be inferred.
    """
    # Explicit user override always wins
    if root := os.environ.get("PROJECT_ROOT"):
        return Path(root)

    # Common dev heuristic: venv lives directly under project root
    if venv := os.environ.get("VIRTUAL_ENV"):
        return Path(venv).parent

    # Fallback: walk upward from CWD looking for project indicators
    cur = Path.cwd().resolve()
    checks = ("pyproject.toml", ".git", "requirements.txt")
    for c in checks:
        for parent in (cur, *cur.parents):
            if (parent / c).exists():
                return parent

    # No markers found; caller must handle absence explicitly
    return None
