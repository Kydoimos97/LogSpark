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


def get_console_width() -> int | None:
    """Query the real terminal width via platform-native APIs, bypassing stdout redirection.

    Tries all three standard handles (stdout, stderr, stdin) in order so that a single
    redirected stream does not prevent detection.  Returns ``None`` when no console is
    attached or all probes fail; never raises.

    - **Windows** — ``GetConsoleScreenBufferInfo`` via ``ctypes``; equivalent to
      ``$Host.UI.RawUI.WindowSize.Width`` in PowerShell.
    - **Linux / macOS** — ``fcntl.ioctl(fd, TIOCGWINSZ)``; works even when stdout is a pipe
      provided at least one handle remains attached to the terminal.
    """
    if os.name == "nt":
        return _get_console_width_windows()
    return _get_console_width_unix()


def _get_console_width_windows() -> int | None:
    """Windows implementation of get_console_width()."""
    try:
        import ctypes
        import ctypes.wintypes

        class _COORD(ctypes.Structure):
            _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

        class _SMALL_RECT(ctypes.Structure):
            _fields_ = [
                ("Left", ctypes.c_short),
                ("Top", ctypes.c_short),
                ("Right", ctypes.c_short),
                ("Bottom", ctypes.c_short),
            ]

        class _CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
            _fields_ = [
                ("dwSize", _COORD),
                ("dwCursorPosition", _COORD),
                ("wAttributes", ctypes.c_ushort),
                ("srWindow", _SMALL_RECT),
                ("dwMaximumWindowSize", _COORD),
            ]

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        invalid = ctypes.wintypes.HANDLE(-1).value

        for std_id in (-11, -12, -10):  # STD_OUTPUT, STD_ERROR, STD_INPUT
            handle = kernel32.GetStdHandle(std_id)
            if not handle or handle == invalid:
                continue
            info = _CONSOLE_SCREEN_BUFFER_INFO()
            if kernel32.GetConsoleScreenBufferInfo(handle, ctypes.byref(info)):
                width = info.srWindow.Right - info.srWindow.Left + 1
                if width > 0:
                    return width
    except Exception:
        pass
    return None


def _get_console_width_unix() -> int | None:
    """Linux/macOS implementation of get_console_width()."""
    try:
        import fcntl
        import struct
        import termios

        for fd in (1, 2, 0):  # stdout, stderr, stdin
            try:
                packed = fcntl.ioctl(fd, termios.TIOCGWINSZ, b"\x00" * 8)
                _rows, cols = struct.unpack("HH", packed[:4])
                if cols > 0:
                    return cols
            except OSError:
                continue
    except Exception:
        pass
    return None


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
