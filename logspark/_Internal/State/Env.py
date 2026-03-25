import os
from importlib.util import find_spec
from pathlib import Path


def is_silenced_mode() -> bool:
    """Return True when LOGSPARK_MODE=silenced; output is routed to devnull while pipelines stay active."""
    return os.getenv("LOGSPARK_MODE", "").lower() == "silenced"


def is_fast_mode() -> bool:
    """Return True when LOGSPARK_MODE=fast; enables constant-time stacklevel resolution instead of frame walking."""
    return os.getenv("LOGSPARK_MODE", "").lower() == "fast"


def is_rich_available() -> bool:
    """Return True when the Rich library is importable."""
    try:
        return find_spec("rich") is not None
    except ValueError:
        # Module present but broken / partially initialized
        return False


def is_ddtrace_available() -> bool:
    """Return True when the ddtrace library is importable."""
    try:
        return find_spec("ddtrace") is not None
    except ValueError:
        # Module present but broken / partially initialized
        return False


def resolve_project_root() -> Path | None:
    """
    Resolve the project root by checking PROJECT_ROOT env var, VIRTUAL_ENV parent,
    then walking upward from CWD for pyproject.toml, .git, or requirements.txt.
    Returns None when no root can be inferred.
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
