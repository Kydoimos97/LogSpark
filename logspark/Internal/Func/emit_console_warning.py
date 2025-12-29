import warnings

from ...Types import IncompatibleConsoleWarning


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
