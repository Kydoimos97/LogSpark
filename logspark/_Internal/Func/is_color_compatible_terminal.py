from __future__ import annotations

import os
import sys
import warnings

from ...Types.Protocol import SupportsWrite


def _is_idle() -> bool:
    """Detect IDLE, which claims to be a TTY but cannot handle ANSI."""
    module = getattr(sys.stdin, "__module__", "")
    return module.startswith("idlelib")


def _is_jupyter() -> bool:
    """Detect Jupyter / Colab / Databricks environments.

    Originally inspired by Rich (https://github.com/Textualize/rich)
    - rich.console._is_jupyter
    MIT License

    """
    try:
        ipython = get_ipython()  # type: ignore[name-defined]
        shell = ipython.__class__.__name__
    except NameError:
        return False

    if (
        "google.colab" in str(ipython.__class__)
        or os.getenv("DATABRICKS_RUNTIME_VERSION")
        or shell == "ZMQInteractiveShell"
        or shell == "HexShell"
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

    # Known bad environments
    if _is_idle():
        return False

    if _is_jupyter():
        return False

    # Explicit overrides
    force_color = os.environ.get("FORCE_COLOR")
    if force_color is not None:
        return force_color != ""

    if os.environ.get("NO_COLOR") is not None:
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

    # Windows conservative fallback
    if os.name == "nt":
        if not os.environ.get("WT_SESSION") and not os.environ.get("ANSICON"):
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

    warnings.warn(
        message=(
            "Rich colored output requested, but the current console does not appear to support ANSI colors.\n"
            "    Rich layout and rendering remain active, but output will not be colored.\n"
            "    Rich output will not be colored and possibly degraded.\n"
            "    To force Rich color usage, set FORCE_COLOR=true in the enviornment or pass a Console(force_terminal=True)."
        ),
        category=RichColorDegradedWarning,
        stacklevel=2,
        source="LogSpark",
    )


def emit_color_incompatible_console_warning() -> None:
    class AnsiColorDegradedWarning(UserWarning):
        """Console does not support color features"""

        pass

    warnings.warn(
        message=(
            "\nColored output requested, but the current console does not appear to support "
            "ANSI escape sequences.\n"
            "    Output will not be colored and possibly degraded.\n"
            "    To force color usage, set FORCE_COLOR=true in the enviornment"
        ),
        category=AnsiColorDegradedWarning,
        stacklevel=2,
        source="LogSpark",
    )
