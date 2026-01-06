import os
import shutil
import sys
import warnings
from typing import Any

from ...Types.Protocol import SupportsWrite

def _is_idle() -> bool:
    """Detect IDLE, which claims to be a TTY but cannot handle ANSI.
    Originally inspired by Rich (https://github.com/Textualize/rich)
    - rich.console.Console.is_terminal
    MIT License
    """
    module = getattr(sys.stdin, "__module__", "")
    return module.startswith("idlelib")


def _is_jupyter() -> bool:
    """Detect Jupyter / Colab / Databricks environments.

    Originally inspired by Rich (https://github.com/Textualize/rich)
    - rich.console._is_jupyter


    """
    try:
        ipython = get_ipython()  # type: ignore[name-defined]  # pragma: no cover
        shell = ipython.__class__.__name__ # pragma: no cover
    except NameError:
        return False

    if (
        "google.colab" in str(ipython.__class__)  # pragma: no cover
        or os.getenv("DATABRICKS_RUNTIME_VERSION")  # pragma: no cover
        or shell == "ZMQInteractiveShell"
        or shell == "HexShell"  # pragma: no cover
    ):
        return True

    return False


def is_color_compatible_terminal(stream: SupportsWrite | None = None) -> bool:
    """
    Terminal color capability detection.

    Originally inspired by Rich (https://github.com/Textualize/rich)
    - rich.console.Console.is_terminal
    - rich.console._is_jupyter
    MIT License

    This implementation is adapted and simplified for LogSpark to:

    - avoid importing Rich as a dependency
    - operate on generic output streams (not Console abstractions)
    - detect *ANSI color capability only*, not interactivity
    - prioritize explicit user intent (FORCE_COLOR / NO_COLOR) over heuristics
    - treat notebook-style environments (Jupyter, Colab, Databricks, Hex) as non-color terminals
    - remain conservative in ambiguous environments (e.g. Windows, redirected IO)

    It intentionally does *not* attempt to detect:
    - cursor movement support
    - alternate screen support
    - terminal interactivity
    - full Rich feature compatibility
    """

    # Explicit overrides
    force_color = os.environ.get("FORCE_COLOR")
    if force_color is not None:
        return force_color != ""

    if os.environ.get("NO_COLOR") is not None:
        return False

    # Known bad environments
    if _is_idle():
        return False

    if _is_jupyter():
        return False

    # Env Variables
    tty_compatible = os.environ.get("TTY_COMPATIBLE", "")
    if tty_compatible == "0":
        return False
    if tty_compatible == "1":
        return True

    term = os.environ.get("TERM", "").lower()
    if term in ("dumb", "unknown"):
        return False


    if os.environ.get('TERMINAL_EMULATOR') is not None and os.environ.get('TERM') is not None:
        return True

    # Windows conservative fallback
    if os.name == "nt" or "Windows" in os.environ.get('OS', ""):
        if os.environ.get("WT_SESSION") or os.environ.get("ANSICON"):
            return True
        else:
            return False

    # Stream-based detection
    if stream is not None:
        isatty = getattr(stream, "isatty", None)
        try:
            if isatty is None or not isatty():
                return False
        except Exception:
            return False

    return True


def emit_color_incompatible_rich_console_warning() -> None:
    class RichColorDegradedWarning(UserWarning):
        """Console does not support requested Rich color features"""

        pass
    from .emit_warning import emit_warning
    emit_warning(
        message=(
            "\nWARNING: Rich colored output requested, \n"
            "    | however the current console does not appear to support ANSI colors.\n"
            "    | Rich layout and rendering remain active, but output will not be colored.\n"
            "    | To force Rich color usage, set FORCE_COLOR=true in the enviornment\n"
            "    | or pass a Console(force_terminal=True)."
        ),
        category=RichColorDegradedWarning,
        stacklevel=4,
    )


def emit_color_incompatible_console_warning() -> None:
    class AnsiColorDegradedWarning(UserWarning):
        """Console does not support color features"""

        pass
    from .emit_warning import emit_warning
    emit_warning(
        message=(
            "\nWARNING: Colored output requested,\n"
            "    | however the current console does not appear to support ANSI escape sequences.\n"
            "    | The Output will not be colored as a result.\n"
            "    | To force color usage, set FORCE_COLOR=true in the enviornment."
        ),
        category=AnsiColorDegradedWarning,
        stacklevel=4,
    )
