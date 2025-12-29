import os
import shutil
import warnings
from io import TextIOWrapper

from ...Types import IncompatibleConsoleWarning


def is_silenced_mode() -> bool:
    """
    When LOGSPARK_MODE=silenced, all logging pipelines remain fully active,
    but output is discarded. This mode is intended for tests and high-volume
    scenarios where logging correctness must be validated without producing output.
    """
    return os.getenv("LOGSPARK_MODE", '').lower() == "silenced"


def is_supported_terminal() -> bool:
    """If height and size aren't available or set the console is generally not supported by rich"""
    if not os.environ.get("FORCE_RICH", "false").lower() == "true":
        _w, _h = shutil.get_terminal_size((0, 0))
        if _w == 0 and _h == 0:
            return False
    return True


def emit_console_warning() -> None:
    warnings.warn_explicit(
        message="\nRich incompatible console detected. \n"
        "    To force rich usage please set the FORCE_RICH environment variable to `true`,\n"
        "    or pass a predefined Rich Console to the TerminalHandler.",
        category=IncompatibleConsoleWarning,
        filename="Terminal.py",
        lineno=34,
        module="LogSpark",
    )


def get_devnull() -> TextIOWrapper:
    devnull = open(
        os.devnull,
        mode="w",
        encoding="utf-8",
        errors="replace",
    )
    return devnull
